# CanXtoDBC
A Simple Ecumaster CANX to DBC converter python script


### Open terminal:
```bash
python canx_to_dbc_ecumaster.py input.canx output.dbc
```

### Example:
```bash
python canx_to_dbc_ecumaster.py Status_B_Can_0xA18A000.canx Status_B.dbc
```

### Output:
- A `.dbc` file will be converted in the current folder.

---

## Functioning

Lo script:
1. Legge la struttura XML del file `.canx` Ecumaster:
   ```xml
   <CANbuseXport>
     <mob id="..." canbusID="..." canbusIF="..." ext="...">
       <frame frequency="...">
         <channel id="..." type="..." byteOffset="..."/>
       </frame>
     </mob>
   </CANbuseXport>
   ```
2. Converte ogni `<mob>` in un **messaggio CAN (`BO_`)**
3. Converte ogni `<channel>` in un **segnale (`SG_`)**
4. Calcola automaticamente la posizione del segnale in bit (`byteOffset × 8`)

---

## Conversion Example

### Input `.canx`
```xml
<mob id="Status_B" canbusID="0xA18A000" canbusIF="0" ext="1">
  <frame frequency="10">
    <channel id="OilTemp" type="Analog" byteOffset="0"/>
    <channel id="OilPressure" type="Analog" byteOffset="1"/>
  </frame>
</mob>
```

### Output `.dbc`
```dbc
BO_ 169328128 Status_B: 8 ECUmaster
 SG_ OilTemp : 0|8@1+ (1,0) [0|255] "" ECUmaster
 SG_ OilPressure : 8|8@1+ (1,0) [0|255] "" ECUmaster
```

---

##  Notes

- `frequency` field is ignored at the moment.
- Every messages are attributed to `ECUmaster` node.

---

