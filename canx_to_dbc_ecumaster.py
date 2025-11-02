import xml.etree.ElementTree as ET
import sys

def canx_to_dbc_ecumaster(canx_path, dbc_path):
    """
    Converte un file Ecumaster .canx (CAN Manager export) in un file .dbc standard.
    Compatibile con i formati Ecumaster PMU, ADU, EMU, ecc.
    """

    tree = ET.parse(canx_path)
    root = tree.getroot()

    dbc = []
    dbc.append('VERSION ""\n\n')
    dbc.append('NS_ :\n')
    dbc.append('  NS_DESC_\n  CM_\n  BA_DEF_\n  BA_\n  VAL_\n  CAT_DEF_\n  CAT_\n  FILTER\n  BA_DEF_DEF_\n  EV_DATA_\n  ENVVAR_DATA_\n  SGTYPE_\n  SGTYPE_VAL_\n  BA_DEF_SGTYPE_\n  BA_SGTYPE_\n  SIG_TYPE_REF_\n  VAL_TABLE_\n  SIG_GROUP_\n  SIG_VALTYPE_\n  SIGTYPE_VALTYPE_\n  BO_TX_BU_\n  BA_DEF_REL_\n  BA_REL_\n  BA_DEF_DEF_REL_\n  BU_SG_REL_\n  BU_EV_REL_\n  BU_BO_REL_\n  SG_MUL_VAL_\n\n')
    dbc.append('BS_:\n\n')
    dbc.append('BU_: ECUmaster\n\n')

    # Ogni "mob" rappresenta un messaggio CAN
    for mob in root.findall(".//mob"):
        msg_name = mob.get("id", "Unknown_MOB")
        can_id = mob.get("canbusID", "0x0")
        ext = mob.get("ext", "0")
        can_id_int = int(can_id, 0)
        msg_dlc = 8  # default se non specificato
        frame = mob.find("frame")

        # Frequenza non serve per il DBC ma può essere usata per commento
        freq = frame.get("frequency", "") if frame is not None else ""

        dbc.append(f"BO_ {can_id_int} {msg_name}: {msg_dlc} ECUmaster\n")

        if frame is not None:
            for i, ch in enumerate(frame.findall("channel")):
                sig_name = ch.get("id", f"Signal_{i}")
                byte_offset = int(ch.get("byteOffset", "0"))
                start_bit = byte_offset * 8  # byte → bit offset
                length = 8  # di default 1 byte
                factor = 1
                offset = 0
                min_val = 0
                max_val = 255
                unit = ""
                dbc.append(f" SG_ {sig_name} : {start_bit}|{length}@1+ ({factor},{offset}) [{min_val}|{max_val}] \"{unit}\" ECUmaster\n")

        dbc.append("\n")

    with open(dbc_path, "w", encoding="utf-8") as f:
        f.writelines(dbc)

    print(f"✅ Conversione completata: {dbc_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python canx_to_dbc_ecumaster.py input.canx output.dbc")
    else:
        canx_to_dbc_ecumaster(sys.argv[1], sys.argv[2])
