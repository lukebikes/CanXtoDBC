# CanXtoDBC
A Simple Ecumaster CANX to DBC converter python script


### Open terminal:
```bash
python canx_to_dbc.py input.canx output.dbc
```

### Example:
```bash
python canx_to_dbc.py Status_B_Can_0xA18A000.canx Status_B.dbc
```

### Output:
- A `.dbc` file will be converted in the current folder.


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
- DLC size calculation can be buggy ant the moment with dlc 9 appearing sometimes

---

