# Li-Lim 100-case comparison

> Official result comparison now reports only the strict solvers: reference, OR-Tools, and Rust.
> The `OR-Tools vs Rust` columns measure OR-Tools relative to Rust, so positive gaps mean OR-Tools is worse than Rust.

| Instance | Ref veh | Ref dist | OR-Tools veh | OR-Tools dist | OR-Tools gap % | OR-Tools status | Rust veh | Rust dist | Rust gap % | Rust status | O-R veh gap | O-R gap % | O-R status |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| lc101 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc102 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc103 | 9 | 1035.35 | 10 | 827.86 | -20.04 | worse_vehicles | 10 | 827.86 | -20.04 | worse_vehicles | +0 | +0.00 | match |
| lc104 | 9 | 860.01 | 9 | 1155.31 | 34.34 | worse_distance | 10 | 859.36 | -0.08 | worse_vehicles | -1 | +34.44 | better_vehicles |
| lc105 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc106 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc107 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc108 | 10 | 826.44 | 10 | 826.44 | 0.00 | match | 10 | 826.44 | 0.00 | match | +0 | +0.00 | match |
| lc109 | 9 | 1000.60 | 10 | 905.14 | -9.54 | worse_vehicles | 10 | 890.99 | -10.95 | worse_vehicles | +0 | +1.59 | worse_distance |
| lc201 | 3 | 591.56 | 3 | 591.56 | 0.00 | match | 3 | 591.56 | 0.00 | match | +0 | +0.00 | match |
| lc202 | 3 | 591.56 | 3 | 591.56 | 0.00 | match | 3 | 591.56 | 0.00 | match | +0 | +0.00 | match |
| lc203 | 3 | 591.17 | 3 | 591.17 | 0.00 | match | 3 | 659.79 | 11.61 | worse_distance | +0 | -10.40 | better_distance |
| lc204 | 3 | 590.60 | 3 | 644.34 | 9.10 | worse_distance | 3 | 673.72 | 14.07 | worse_distance | +0 | -4.36 | better_distance |
| lc205 | 3 | 588.88 | 3 | 588.88 | 0.00 | match | 3 | 588.88 | 0.00 | match | +0 | +0.00 | match |
| lc206 | 3 | 588.49 | 3 | 588.49 | 0.00 | match | 3 | 588.49 | 0.00 | match | +0 | +0.00 | match |
| lc207 | 3 | 588.29 | 3 | 588.29 | 0.00 | match | 3 | 588.29 | 0.00 | match | +0 | +0.00 | match |
| lc208 | 3 | 588.32 | 3 | 591.77 | 0.59 | worse_distance | 3 | 591.62 | 0.56 | worse_distance | +0 | +0.03 | worse_distance |
| lr101 | 19 | 1650.80 | 20 | 1662.09 | 0.68 | worse_vehicles | 19 | 1650.80 | 0.00 | match | +1 | +0.68 | worse_vehicles |
| lr102 | 17 | 1487.57 | 18 | 1571.62 | 5.65 | worse_vehicles | 18 | 1623.73 | 9.15 | worse_vehicles | +0 | -3.21 | better_distance |
| lr103 | 13 | 1292.68 | 15 | 1458.61 | 12.84 | worse_vehicles | 13 | 1325.58 | 2.55 | worse_distance | +2 | +10.04 | worse_vehicles |
| lr104 | 9 | 1013.39 | 11 | 1158.06 | 14.28 | worse_vehicles | 11 | 1176.15 | 16.06 | worse_vehicles | +0 | -1.54 | better_distance |
| lr105 | 14 | 1377.11 | 14 | 1377.11 | 0.00 | match | 14 | 1377.11 | 0.00 | match | +0 | +0.00 | match |
| lr106 | 12 | 1252.62 | 12 | 1272.78 | 1.61 | worse_distance | 14 | 1347.77 | 7.60 | worse_vehicles | -2 | -5.56 | better_vehicles |
| lr107 | 10 | 1111.31 | 11 | 1187.77 | 6.88 | worse_vehicles | 11 | 1138.56 | 2.45 | worse_vehicles | +0 | +4.32 | worse_distance |
| lr108 | 9 | 968.97 | 10 | 1028.63 | 6.16 | worse_vehicles | 10 | 1029.00 | 6.20 | worse_vehicles | +0 | -0.04 | better_distance |
| lr109 | 11 | 1208.96 | 14 | 1458.50 | 20.64 | worse_vehicles | 13 | 1281.95 | 6.04 | worse_vehicles | +1 | +13.77 | worse_vehicles |
| lr110 | 10 | 1159.35 | 12 | 1269.82 | 9.53 | worse_vehicles | 13 | 1288.09 | 11.10 | worse_vehicles | -1 | -1.42 | better_vehicles |
| lr111 | 10 | 1108.90 | 12 | 1197.24 | 7.97 | worse_vehicles | 12 | 1202.45 | 8.44 | worse_vehicles | +0 | -0.43 | better_distance |
| lr112 | 9 | 1003.77 | 10 | 1148.84 | 14.45 | worse_vehicles | 11 | 1222.13 | 21.75 | worse_vehicles | -1 | -6.00 | better_vehicles |
| lr201 | 4 | 1253.23 | 4 | 1348.88 | 7.63 | worse_distance | 4 | 1279.90 | 2.13 | worse_distance | +0 | +5.39 | worse_distance |
| lr202 | 3 | 1197.67 | 4 | 1484.89 | 23.98 | worse_vehicles | 4 | 1327.02 | 10.80 | worse_vehicles | +0 | +11.90 | worse_distance |
| lr203 | 3 | 949.40 | 4 | 1168.82 | 23.11 | worse_vehicles | 4 | 1202.00 | 26.61 | worse_vehicles | +0 | -2.76 | better_distance |
| lr204 | 2 | 849.05 | 3 | 1106.99 | 30.38 | worse_vehicles | 3 | 963.21 | 13.45 | worse_vehicles | +0 | +14.93 | worse_distance |
| lr205 | 3 | 1054.02 | 4 | 1343.32 | 27.45 | worse_vehicles | 4 | 1133.77 | 7.57 | worse_vehicles | +0 | +18.48 | worse_distance |
| lr206 | 3 | 931.63 | 3 | 1035.28 | 11.13 | worse_distance | 3 | 965.90 | 3.68 | worse_distance | +0 | +7.18 | worse_distance |
| lr207 | 2 | 903.06 | 4 | 1169.75 | 29.53 | worse_vehicles | 3 | 1165.67 | 29.08 | worse_vehicles | +1 | +0.35 | worse_vehicles |
| lr208 | 2 | 734.85 | 3 | 947.49 | 28.94 | worse_vehicles | 2 | 734.85 | 0.00 | match | +1 | +28.94 | worse_vehicles |
| lr209 | 3 | 930.59 | 4 | 1159.62 | 24.61 | worse_vehicles | 4 | 1023.12 | 9.94 | worse_vehicles | +0 | +13.34 | worse_distance |
| lr210 | 3 | 964.22 | 5 | 1238.34 | 28.43 | worse_vehicles | 3 | 1013.20 | 5.08 | worse_distance | +2 | +22.22 | worse_vehicles |
| lr211 | 2 | 911.52 | 3 | 1116.77 | 22.52 | worse_vehicles | 3 | 1002.85 | 10.02 | worse_vehicles | +0 | +11.36 | worse_distance |
| lrc101 | 14 | 1708.80 | 16 | 1749.03 | 2.35 | worse_vehicles | 17 | 1853.73 | 8.48 | worse_vehicles | -1 | -5.65 | better_vehicles |
| lrc102 | 12 | 1558.07 | 15 | 1675.59 | 7.54 | worse_vehicles | 14 | 1627.97 | 4.49 | worse_vehicles | +1 | +2.93 | worse_vehicles |
| lrc103 | 11 | 1258.74 | 11 | 1279.94 | 1.68 | worse_distance | 13 | 1633.35 | 29.76 | worse_vehicles | -2 | -21.64 | better_vehicles |
| lrc104 | 10 | 1128.40 | 11 | 1170.62 | 3.74 | worse_vehicles | 11 | 1235.61 | 9.50 | worse_vehicles | +0 | -5.26 | better_distance |
| lrc105 | 13 | 1637.62 | 14 | 1653.71 | 0.98 | worse_vehicles | 14 | 1705.65 | 4.15 | worse_vehicles | +0 | -3.05 | better_distance |
| lrc106 | 11 | 1424.73 | 14 | 1589.64 | 11.57 | worse_vehicles | 14 | 1585.55 | 11.29 | worse_vehicles | +0 | +0.26 | worse_distance |
| lrc107 | 11 | 1230.14 | 12 | 1285.93 | 4.54 | worse_vehicles | 13 | 1452.33 | 18.06 | worse_vehicles | -1 | -11.46 | better_vehicles |
| lrc108 | 10 | 1147.43 | 12 | 1309.01 | 14.08 | worse_vehicles | 11 | 1362.68 | 18.76 | worse_vehicles | +1 | -3.94 | worse_vehicles |
| lrc201 | 4 | 1406.94 | 5 | 1498.25 | 6.49 | worse_vehicles | 5 | 1700.10 | 20.84 | worse_vehicles | +0 | -11.87 | better_distance |
| lrc202 | 3 | 1374.27 | 4 | 1463.41 | 6.49 | worse_vehicles | 4 | 1735.99 | 26.32 | worse_vehicles | +0 | -15.70 | better_distance |
| lrc203 | 3 | 1089.07 | 4 | 1643.75 | 50.93 | worse_vehicles | 4 | 1162.21 | 6.72 | worse_vehicles | +0 | +41.43 | worse_distance |
| lrc204 | 3 | 818.66 | 4 | 909.18 | 11.06 | worse_vehicles | 4 | 887.32 | 8.39 | worse_vehicles | +0 | +2.46 | worse_distance |
| lrc205 | 4 | 1302.20 | 4 | 1302.20 | 0.00 | match | 5 | 1402.29 | 7.69 | worse_vehicles | -1 | -7.14 | better_vehicles |
| lrc206 | 3 | 1159.03 | 4 | 1595.94 | 37.70 | worse_vehicles | 4 | 1369.31 | 18.14 | worse_vehicles | +0 | +16.55 | worse_distance |
| lrc207 | 3 | 1062.05 | 5 | 1715.62 | 61.54 | worse_vehicles | 4 | 1236.14 | 16.39 | worse_vehicles | +1 | +38.79 | worse_vehicles |
| lrc208 | 3 | 852.76 | 4 | 1155.05 | 35.45 | worse_vehicles | 4 | 1049.83 | 23.11 | worse_vehicles | +0 | +10.02 | worse_distance |

## Aggregate

- Instances compared: 56

### OR-Tools strict model

- Reported feasible instances in the OR-Tools model: 56 / 56
- Strict feasible instances: 56 / 56
- Exact matches to reference: 14
- Same vehicle count as reference on strict-feasible cases: 21
- Better vehicle count than reference on strict-feasible cases: 0
- Worse vehicle count than reference on strict-feasible cases: 35
- Average distance gap on strict-feasible cases: 11.23%
- Average distance gap on same-vehicle strict-feasible cases: 3.15%

### Rust ALNS

- Strict feasible instances: 56 / 56
- Exact matches to reference: 14
- Same vehicle count as reference on strict-feasible cases: 21
- Better vehicle count than reference on strict-feasible cases: 0
- Worse vehicle count than reference on strict-feasible cases: 35
- Average distance gap on strict-feasible cases: 7.80%
- Average distance gap on same-vehicle strict-feasible cases: 1.89%

### OR-Tools vs Rust

- Cases where both solvers are strict feasible: 56 / 56
- Exact matches between OR-Tools and Rust: 13
- Same vehicle count between OR-Tools and Rust: 39
- OR-Tools better vehicle count than Rust: 8
- Rust better vehicle count than OR-Tools: 9
- OR-Tools better distance than Rust on same-vehicle cases: 11
- Rust better distance than OR-Tools on same-vehicle cases: 15
- Average OR-Tools distance gap vs Rust: 3.39%
- Average OR-Tools distance gap vs Rust on same-vehicle cases: 2.58%
