#!/usr/bin/env python3
"""
canx2dbc_dbg.py  (rev with forced LE channels in multiplexed frames)
"""

import sys, argparse, xml.etree.ElementTree as ET, re
from typing import Optional

def safe_int(v: Optional[str], default: int = 0) -> int:
    if v is None: return default
    s = str(v).strip()
    if s == "": return default
    try:
        return int(s, 0)
    except:
        try: return int(float(s))
        except: return default

def safe_float(v: Optional[str], default: float = 0.0) -> float:
    if v is None: return default
    s = str(v).strip()
    if s == "": return default
    try:
        return float(s)
    except:
        return default

def parse_canid_hex(cid_raw: str) -> int:
    if cid_raw is None: raise ValueError("Missing canbusID")
    s = cid_raw.strip().lower()
    if s.startswith("0x"): s = s[2:]
    try: return int(s, 16)
    except: return safe_int(cid_raw, 0)

def extract_compound_bits(compound_type: Optional[str]) -> Optional[int]:
    if not compound_type: return None
    m = re.search(r'Compound(\d+)', compound_type)
    return int(m.group(1)) if m else None

def motorola_startbit(byte_offset:int, bit_position:int) -> int:
    return byte_offset*8 + (7 - bit_position)

def intel_startbit(byte_offset:int, bit_position:int) -> int:
    return byte_offset*8 + bit_position

def endian_flag_from_str(endian_str: str) -> int:
    return 0 if str(endian_str).lower().startswith("b") else 1

def infer_bitcount_from_type(type_str: Optional[str]) -> int:
    if not type_str: return 8
    t = type_str.lower()
    if "64" in t: return 64
    if "32" in t: return 32
    if "16" in t: return 16
    return 8

def sanitize_name(n: str) -> str:
    n = re.sub(r'[^0-9A-Za-z_\.]', '_', n)
    return n.replace(".", "_")   # FIX: remove dot

def build_signals_from_frame(frame_elem, frame_mux_value: Optional[int],
                             compound_endian: Optional[str], is_compound: bool,
                             debug=False):
    signals=[]
    for ch in frame_elem.findall("channel"):
        name_raw = ch.get("id") or ""
        name = sanitize_name(name_raw)

        byte_offset = safe_int(ch.get("byteOffset"), 0)
        bitpos = safe_int(ch.get("bitPosition"), 0)

        bitcnt_attr = ch.get("bitCount")
        bitcount = infer_bitcount_from_type(ch.get("type")) \
                   if (bitcnt_attr is None or bitcnt_attr.strip()=="") \
                   else safe_int(bitcnt_attr,8)

        # ------------------------------
        # NEW FIX: in compound mode all channels are LITTLE-ENDIAN
        # ------------------------------
        if is_compound:
            ch_endian = "le"
        else:
            type_str = ch.get("type","")
            if "be" in type_str.lower(): ch_endian = "be"
            elif "le" in type_str.lower(): ch_endian = "le"
            else: ch_endian = "le"

        if ch_endian == "be":
            startbit = motorola_startbit(byte_offset, bitpos)
        else:
            startbit = intel_startbit(byte_offset, bitpos)

        mult = safe_float(ch.get("multiplier"), 1.0)
        div = safe_float(ch.get("divider"), 1.0)
        scale = mult/div if div!=0 else mult
        offset = safe_float(ch.get("offset"), 0.0)
        unit = (ch.get("unit") or "").replace('"','')

        sig = {
            "name": name,
            "orig_name": name_raw,
            "startbit": startbit,
            "length": bitcount,
            "endian": ch_endian,
            "endian_flag": endian_flag_from_str(ch_endian),
            "scale": scale,
            "offset": offset,
            "unit": unit,
            "mux": frame_mux_value
        }
        signals.append(sig)

        if debug:
            sys.stderr.write(
                f"  CH {name_raw} -> {name}  mux={frame_mux_value} "
                f"byteOff={byte_offset} bit={bitpos} len={bitcount} "
                f"endian={ch_endian} start={startbit}\n"
            )

    return signals

def convert_canx_to_messages(root, debug=False):
    messages=[]

    for mob in root.findall(".//mob"):
        msg_name_raw = mob.get("id") or "MSG"
        msg_name = sanitize_name(msg_name_raw)

        base_id = parse_canid_hex(mob.get("canbusID"))
        declared_width = safe_int(mob.get("width"), 0)

        mob_type = mob.get("type","")
        compound_bits = extract_compound_bits(mob_type)
        is_compound = compound_bits is not None

        compound_pos = safe_int(mob.get("compoundBitPosition"), 0) if is_compound else None
        compound_offset = safe_int(mob.get("compoundOffset"), 0)
        compound_endian = mob.get("compoundEndian","be").lower()

        frames = mob.findall("frame")
        if not frames:
            frames=[mob]

        if debug:
            sys.stderr.write(
                f"\n=== MOB {msg_name_raw} 0x{base_id:X}  compound={is_compound} frames={len(frames)}\n"
            )

        # ------------------------------------------------------------
        # MULTIPLEXED MESSAGE
        # ------------------------------------------------------------
        if is_compound:
            all_signals=[]

            for fr in frames:
                muxv = safe_int(fr.get("offset"), 0)
                sigs = build_signals_from_frame(fr, muxv, compound_endian,
                                                is_compound=True, debug=debug)
                all_signals.extend(sigs)

            max_used_byte = -1
            for s in all_signals:
                last_bit = s["startbit"] + s["length"] - 1
                last_byte = last_bit // 8
                if last_byte > max_used_byte:
                    max_used_byte = last_byte

            # -------------------------------
            # FIX: MUX position (Motorola rule OK)
            # -------------------------------
            mux_len = compound_bits
            if compound_endian == "be":
                mux_start = (compound_offset*8) + (compound_pos + mux_len - 1)
            else:
                mux_start = (compound_offset*8) + compound_pos

            mux_last_bit = mux_start + mux_len - 1
            mux_last_byte = mux_last_bit // 8
            max_used_byte = max(max_used_byte, mux_last_byte)

            dlc_detect = max_used_byte+1
            dlc_final = max(declared_width, dlc_detect) if declared_width>0 else (dlc_detect if dlc_detect>0 else 8)

            messages.append({
                "id": base_id,
                "name": msg_name,
                "dlc": dlc_final,
                "is_compound": True,
                "mux": {
                    "name":"MUX",
                    "startbit": mux_start,
                    "length": mux_len,
                    "endian_flag": endian_flag_from_str(compound_endian)
                },
                "signals": all_signals
            })
            continue

        # ------------------------------------------------------------
        # NON-MULTIPLEXED MESSAGE
        # ------------------------------------------------------------
        for fr in frames:
            offset = safe_int(fr.get("offset"),0)
            real_id = base_id + offset

            sigs = build_signals_from_frame(fr, None, None,
                                            is_compound=False, debug=debug)

            max_used_byte=-1
            for s in sigs:
                last_bit = s["startbit"] + s["length"] - 1
                last_byte = last_bit // 8
                if last_byte > max_used_byte:
                    max_used_byte=last_byte

            dlc_detect = max_used_byte+1
            dlc_final = max(declared_width, dlc_detect) if declared_width>0 else (dlc_detect if dlc_detect>0 else 8)

            messages.append({
                "id": real_id,
                "name": f"{msg_name}_f{offset}",
                "dlc": dlc_final,
                "is_compound": False,
                "mux": None,
                "signals": sigs
            })

    return messages

def write_dbc_file(filename, messages):
    with open(filename,"w",encoding="utf-8") as f:
        f.write('VERSION "generated by canx2dbc"\n\n')
        f.write("NS_ :\n\nBS_:\n\nBU_: Vector__XXX\n\n")

        for m in messages:
            f.write(f"BO_ {m['id']} {m['name']}: {m['dlc']} Vector__XXX\n")

            if m["is_compound"]:
                mux = m["mux"]
                f.write(
                    f" SG_ {mux['name']} M : "
                    f"{mux['startbit']}|{mux['length']}@{mux['endian_flag']}+ "
                    f"(1,0) [0|{(2**mux['length'])-1}] \"\" Vector__XXX\n"
                )

                sigs_sorted = sorted(m["signals"], key=lambda s: (s["mux"], s["startbit"]))
                for s in sigs_sorted:
                    f.write(
                        f" SG_ {s['name']} m{s['mux']} : "
                        f"{s['startbit']}|{s['length']}@{s['endian_flag']}+ "
                        f"({s['scale']},{s['offset']}) [0|0] "
                        f"\"{s['unit']}\" Vector__XXX\n"
                    )

            else:
                sigs_sorted = sorted(m["signals"], key=lambda s: s["startbit"])
                for s in sigs_sorted:
                    f.write(
                        f" SG_ {s['name']} : "
                        f"{s['startbit']}|{s['length']}@{s['endian_flag']}+ "
                        f"({s['scale']},{s['offset']}) [0|0] "
                        f"\"{s['unit']}\" Vector__XXX\n"
                    )

            f.write("\n")

    print(f"[OK] wrote {filename}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--debug", action="store_true")
    args=ap.parse_args()

    try:
        tree = ET.parse(args.input)
    except Exception as e:
        print("Error parsing input:", e, file=sys.stderr)
        sys.exit(2)

    root = tree.getroot()
    msgs = convert_canx_to_messages(root, debug=args.debug)
    write_dbc_file(args.output, msgs)

if __name__ == "__main__":
    main()
