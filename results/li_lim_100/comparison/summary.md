# Li-Lim 100-case comparison

> Official result comparison now reports only the strict solvers: reference, OR-Tools, and Rust.
> The `OR-Tools vs Rust` columns measure OR-Tools relative to Rust, so positive gaps mean OR-Tools is worse than Rust.

| Instance | Ref veh | Ref dist | OR-Tools veh | OR-Tools dist | OR-Tools gap % | OR-Tools status | Rust veh | Rust dist | Rust gap % | Rust status | O-R veh gap | O-R gap % | O-R status |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| lc101 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc102 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc103 | 9 | 1035.35 | 10 | 827.86 | -20.04 | worse_vehicles | 10 | 827.86 | -20.04 | worse_vehicles | +0 | +0.00 | match |
| lc104 | 9 | 860.01 | 9 | 1155.31 | 34.34 | worse_distance | 10 | 819.45 | -4.72 | worse_vehicles | -1 | +40.99 | better_vehicles |
| lc105 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc106 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc107 | 10 | 828.94 | 10 | 828.94 | 0.00 | match | 10 | 828.94 | 0.00 | match | +0 | +0.00 | match |
| lc108 | 10 | 826.44 | 10 | 826.44 | 0.00 | match | 10 | 826.44 | 0.00 | match | +0 | +0.00 | match |
| lc109 | 9 | 1000.60 | 10 | 905.14 | -9.54 | worse_vehicles | 10 | 866.86 | -13.37 | worse_vehicles | +0 | +4.42 | worse_distance |
| lc201 | 3 | 591.56 | 3 | 591.56 | 0.00 | match | 3 | 591.56 | 0.00 | match | +0 | +0.00 | match |
| lc202 | 3 | 591.56 | 3 | 591.56 | 0.00 | match | 3 | 591.56 | 0.00 | match | +0 | +0.00 | match |
| lc203 | 3 | 591.17 | 3 | 591.17 | 0.00 | match | 3 | 642.26 | 8.64 | worse_distance | +0 | -7.95 | better_distance |
| lc204 | 3 | 590.60 | 3 | 644.34 | 9.10 | worse_distance | 4 | 744.07 | 25.99 | worse_vehicles | -1 | -13.40 | better_vehicles |
| lc205 | 3 | 588.88 | 3 | 588.88 | 0.00 | match | 3 | 588.88 | 0.00 | match | +0 | +0.00 | match |
| lc206 | 3 | 588.49 | 3 | 588.49 | 0.00 | match | 3 | 588.49 | 0.00 | match | +0 | +0.00 | match |
| lc207 | 3 | 588.29 | 3 | 588.29 | 0.00 | match | 3 | 588.29 | 0.00 | match | +0 | +0.00 | match |
| lc208 | 3 | 588.32 | 3 | 591.77 | 0.59 | worse_distance | 3 | 588.32 | 0.00 | match | +0 | +0.59 | worse_distance |
| lr101 | 19 | 1650.80 | 20 | 1662.09 | 0.68 | worse_vehicles | 20 | 1698.72 | 2.90 | worse_vehicles | +0 | -2.16 | better_distance |
| lr102 | 17 | 1487.57 | 18 | 1571.62 | 5.65 | worse_vehicles | 17 | 1510.82 | 1.56 | worse_distance | +1 | +4.02 | worse_vehicles |
| lr103 | 13 | 1292.68 | 15 | 1458.61 | 12.84 | worse_vehicles | 13 | 1293.14 | 0.04 | worse_distance | +2 | +12.80 | worse_vehicles |
| lr104 | 9 | 1013.39 | 11 | 1158.06 | 14.28 | worse_vehicles | 11 | 1095.72 | 8.12 | worse_vehicles | +0 | +5.69 | worse_distance |
| lr105 | 14 | 1377.11 | 14 | 1377.11 | 0.00 | match | 14 | 1377.11 | 0.00 | match | +0 | +0.00 | match |
| lr106 | 12 | 1252.62 | 12 | 1272.78 | 1.61 | worse_distance | 13 | 1289.33 | 2.93 | worse_vehicles | -1 | -1.28 | better_vehicles |
| lr107 | 10 | 1111.31 | 11 | 1187.77 | 6.88 | worse_vehicles | 12 | 1291.99 | 16.26 | worse_vehicles | -1 | -8.07 | better_vehicles |
| lr108 | 9 | 968.97 | 10 | 1028.63 | 6.16 | worse_vehicles | 9 | 968.97 | 0.00 | match | +1 | +6.16 | worse_vehicles |
| lr109 | 11 | 1208.96 | 14 | 1458.50 | 20.64 | worse_vehicles | 13 | 1367.35 | 13.10 | worse_vehicles | +1 | +6.67 | worse_vehicles |
| lr110 | 10 | 1159.35 | 12 | 1269.82 | 9.53 | worse_vehicles | 12 | 1257.13 | 8.43 | worse_vehicles | +0 | +1.01 | worse_distance |
| lr111 | 10 | 1108.90 | 12 | 1197.24 | 7.97 | worse_vehicles | 13 | 1261.27 | 13.74 | worse_vehicles | -1 | -5.08 | better_vehicles |
| lr112 | 9 | 1003.77 | 10 | 1148.84 | 14.45 | worse_vehicles | 12 | 1172.96 | 16.86 | worse_vehicles | -2 | -2.06 | better_vehicles |
| lr201 | 4 | 1253.23 | 4 | 1348.88 | 7.63 | worse_distance | 7 | 1382.40 | 10.31 | worse_vehicles | -3 | -2.42 | better_vehicles |
| lr202 | 3 | 1197.67 | 4 | 1484.89 | 23.98 | worse_vehicles | 4 | 1267.65 | 5.84 | worse_vehicles | +0 | +17.14 | worse_distance |
| lr203 | 3 | 949.40 | 4 | 1168.82 | 23.11 | worse_vehicles | 4 | 1123.38 | 18.33 | worse_vehicles | +0 | +4.04 | worse_distance |
| lr204 | 2 | 849.05 | 3 | 1106.99 | 30.38 | worse_vehicles | 3 | 1002.62 | 18.09 | worse_vehicles | +0 | +10.41 | worse_distance |
| lr205 | 3 | 1054.02 | 4 | 1343.32 | 27.45 | worse_vehicles | 5 | 1205.03 | 14.33 | worse_vehicles | -1 | +11.48 | better_vehicles |
| lr206 | 3 | 931.63 | 3 | 1035.28 | 11.13 | worse_distance | 5 | 1250.65 | 34.24 | worse_vehicles | -2 | -17.22 | better_vehicles |
| lr207 | 2 | 903.06 | 4 | 1169.75 | 29.53 | worse_vehicles | 4 | 1106.60 | 22.54 | worse_vehicles | +0 | +5.71 | worse_distance |
| lr208 | 2 | 734.85 | 3 | 947.49 | 28.94 | worse_vehicles | 3 | 797.99 | 8.59 | worse_vehicles | +0 | +18.73 | worse_distance |
| lr209 | 3 | 930.59 | 4 | 1159.62 | 24.61 | worse_vehicles | 4 | 1100.32 | 18.24 | worse_vehicles | +0 | +5.39 | worse_distance |
| lr210 | 3 | 964.22 | 5 | 1238.34 | 28.43 | worse_vehicles | 4 | 1038.63 | 7.72 | worse_vehicles | +1 | +19.23 | worse_vehicles |
| lr211 | 2 | 911.52 | 3 | 1116.77 | 22.52 | worse_vehicles | 4 | 1021.44 | 12.06 | worse_vehicles | -1 | +9.33 | better_vehicles |
| lrc101 | 14 | 1708.80 | 16 | 1749.03 | 2.35 | worse_vehicles | 17 | 1807.84 | 5.80 | worse_vehicles | -1 | -3.25 | better_vehicles |
| lrc102 | 12 | 1558.07 | 15 | 1675.59 | 7.54 | worse_vehicles | 13 | 1619.40 | 3.94 | worse_vehicles | +2 | +3.47 | worse_vehicles |
| lrc103 | 11 | 1258.74 | 11 | 1279.94 | 1.68 | worse_distance | 12 | 1351.31 | 7.35 | worse_vehicles | -1 | -5.28 | better_vehicles |
| lrc104 | 10 | 1128.40 | 11 | 1170.62 | 3.74 | worse_vehicles | 11 | 1252.98 | 11.04 | worse_vehicles | +0 | -6.57 | better_distance |
| lrc105 | 13 | 1637.62 | 14 | 1653.71 | 0.98 | worse_vehicles | 14 | 1649.88 | 0.75 | worse_vehicles | +0 | +0.23 | worse_distance |
| lrc106 | 11 | 1424.73 | 14 | 1589.64 | 11.57 | worse_vehicles | 14 | 1580.43 | 10.93 | worse_vehicles | +0 | +0.58 | worse_distance |
| lrc107 | 11 | 1230.14 | 12 | 1285.93 | 4.54 | worse_vehicles | 13 | 1410.99 | 14.70 | worse_vehicles | -1 | -8.86 | better_vehicles |
| lrc108 | 10 | 1147.43 | 12 | 1309.01 | 14.08 | worse_vehicles | 12 | 1372.63 | 19.63 | worse_vehicles | +0 | -4.63 | better_distance |
| lrc201 | 4 | 1406.94 | 5 | 1498.25 | 6.49 | worse_vehicles | 7 | 1585.66 | 12.70 | worse_vehicles | -2 | -5.51 | better_vehicles |
| lrc202 | 3 | 1374.27 | 4 | 1463.41 | 6.49 | worse_vehicles | 5 | 1483.96 | 7.98 | worse_vehicles | -1 | -1.38 | better_vehicles |
| lrc203 | 3 | 1089.07 | 4 | 1643.75 | 50.93 | worse_vehicles | 4 | 1251.95 | 14.96 | worse_vehicles | +0 | +31.30 | worse_distance |
| lrc204 | 3 | 818.66 | 4 | 909.18 | 11.06 | worse_vehicles | 4 | 886.91 | 8.34 | worse_vehicles | +0 | +2.51 | worse_distance |
| lrc205 | 4 | 1302.20 | 4 | 1302.20 | 0.00 | match | 6 | 1393.39 | 7.00 | worse_vehicles | -2 | -6.54 | better_vehicles |
| lrc206 | 3 | 1159.03 | 4 | 1595.94 | 37.70 | worse_vehicles | 5 | 1230.30 | 6.15 | worse_vehicles | -1 | +29.72 | better_vehicles |
| lrc207 | 3 | 1062.05 | 5 | 1715.62 | 61.54 | worse_vehicles | 4 | 1281.22 | 20.64 | worse_vehicles | +1 | +33.91 | worse_vehicles |
| lrc208 | 3 | 852.76 | 4 | 1155.05 | 35.45 | worse_vehicles | 4 | 1110.50 | 30.22 | worse_vehicles | +0 | +4.01 | worse_distance |

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
- Same vehicle count as reference on strict-feasible cases: 17
- Better vehicle count than reference on strict-feasible cases: 0
- Worse vehicle count than reference on strict-feasible cases: 39
- Average distance gap on strict-feasible cases: 7.73%
- Average distance gap on same-vehicle strict-feasible cases: 0.60%

### OR-Tools vs Rust

- Cases where both solvers are strict feasible: 56 / 56
- Exact matches between OR-Tools and Rust: 13
- Same vehicle count between OR-Tools and Rust: 32
- OR-Tools better vehicle count than Rust: 17
- Rust better vehicle count than OR-Tools: 7
- OR-Tools better distance than Rust on same-vehicle cases: 4
- Rust better distance than OR-Tools on same-vehicle cases: 15
- Average OR-Tools distance gap vs Rust: 3.35%
- Average OR-Tools distance gap vs Rust on same-vehicle cases: 2.83%
