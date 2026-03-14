# Li-Lim 100-case comparison

> PyVRP uses a relaxed formulation because its public API does not expose Li-Lim pickup-delivery sibling constraints. The table below reports strict feasibility after re-evaluating the generated route sequence with the benchmark evaluator.

| Instance | Ref veh | Ref dist | PyVRP veh | PyVRP dist | PyVRP gap % | PyVRP feasible | PyVRP status | Rust veh | Rust dist | Rust gap % | Rust feasible | Rust status |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- |
| lc101 | 10 | 828.94 | 11 | 897.49 | 8.27 | no | infeasible | 10 | 828.94 | 0.00 | yes | match |
| lc102 | 10 | 828.94 | 12 | 974.96 | 17.62 | no | infeasible | 10 | 828.94 | 0.00 | yes | match |
| lc103 | 9 | 1035.35 | 11 | 881.67 | -14.84 | no | infeasible | 10 | 827.86 | -20.04 | yes | worse_vehicles |
| lc104 | 9 | 860.01 | 11 | 925.39 | 7.60 | no | infeasible | 10 | 819.45 | -4.72 | yes | worse_vehicles |
| lc105 | 10 | 828.94 | 10 | 939.37 | 13.32 | no | infeasible | 10 | 828.94 | 0.00 | yes | match |
| lc106 | 10 | 828.94 | 10 | 866.68 | 4.55 | no | infeasible | 10 | 828.94 | 0.00 | yes | match |
| lc107 | 10 | 828.94 | 11 | 930.38 | 12.24 | no | infeasible | 10 | 828.94 | 0.00 | yes | match |
| lc108 | 10 | 826.44 | 11 | 907.70 | 9.83 | no | infeasible | 10 | 826.44 | 0.00 | yes | match |
| lc109 | 9 | 1000.60 | 11 | 883.21 | -11.73 | no | infeasible | 10 | 866.86 | -13.37 | yes | worse_vehicles |
| lc201 | 3 | 591.56 | 3 | 591.56 | 0.00 | yes | match | 3 | 591.56 | 0.00 | yes | match |
| lc202 | 3 | 591.56 | 5 | 684.61 | 15.73 | no | infeasible | 3 | 591.56 | 0.00 | yes | match |
| lc203 | 3 | 591.17 | 5 | 671.80 | 13.64 | no | infeasible | 3 | 642.26 | 8.64 | yes | worse_distance |
| lc204 | 3 | 590.60 | 4 | 708.12 | 19.90 | no | infeasible | 4 | 744.07 | 25.99 | yes | worse_vehicles |
| lc205 | 3 | 588.88 | 3 | 588.88 | 0.00 | yes | match | 3 | 588.88 | 0.00 | yes | match |
| lc206 | 3 | 588.49 | 3 | 588.49 | 0.00 | yes | match | 3 | 588.49 | 0.00 | yes | match |
| lc207 | 3 | 588.29 | 3 | 588.29 | 0.00 | yes | match | 3 | 588.29 | 0.00 | yes | match |
| lc208 | 3 | 588.32 | 3 | 588.32 | 0.00 | yes | match | 3 | 588.32 | 0.00 | yes | match |
| lr101 | 19 | 1650.80 | 21 | 1706.35 | 3.37 | no | infeasible | 20 | 1698.72 | 2.90 | yes | worse_vehicles |
| lr102 | 17 | 1487.57 | 21 | 1589.43 | 6.85 | no | infeasible | 17 | 1510.82 | 1.56 | yes | worse_distance |
| lr103 | 13 | 1292.68 | 15 | 1285.50 | -0.56 | no | infeasible | 13 | 1293.14 | 0.04 | yes | worse_distance |
| lr104 | 9 | 1013.39 | 13 | 1079.17 | 6.49 | no | infeasible | 11 | 1095.72 | 8.12 | yes | worse_vehicles |
| lr105 | 14 | 1377.11 | 18 | 1506.09 | 9.37 | no | infeasible | 14 | 1377.11 | 0.00 | yes | match |
| lr106 | 12 | 1252.62 | 17 | 1407.16 | 12.34 | no | infeasible | 13 | 1289.33 | 2.93 | yes | worse_vehicles |
| lr107 | 10 | 1111.31 | 13 | 1155.10 | 3.94 | no | infeasible | 12 | 1291.99 | 16.26 | yes | worse_vehicles |
| lr108 | 9 | 968.97 | 12 | 1016.79 | 4.94 | no | infeasible | 9 | 968.97 | 0.00 | yes | match |
| lr109 | 11 | 1208.96 | 15 | 1264.82 | 4.62 | no | infeasible | 13 | 1367.35 | 13.10 | yes | worse_vehicles |
| lr110 | 10 | 1159.35 | 14 | 1171.71 | 1.07 | no | infeasible | 12 | 1257.13 | 8.43 | yes | worse_vehicles |
| lr111 | 10 | 1108.90 | 14 | 1143.94 | 3.16 | no | infeasible | 13 | 1261.27 | 13.74 | yes | worse_vehicles |
| lr112 | 9 | 1003.77 | 12 | 1065.28 | 6.13 | no | infeasible | 12 | 1172.96 | 16.86 | yes | worse_vehicles |
| lr201 | 4 | 1253.23 | 6 | 1194.18 | -4.71 | no | infeasible | 7 | 1382.40 | 10.31 | yes | worse_vehicles |
| lr202 | 3 | 1197.67 | 11 | 1200.02 | 0.20 | no | infeasible | 4 | 1267.65 | 5.84 | yes | worse_vehicles |
| lr203 | 3 | 949.40 | 7 | 910.74 | -4.07 | no | infeasible | 4 | 1123.38 | 18.33 | yes | worse_vehicles |
| lr204 | 2 | 849.05 | 5 | 770.80 | -9.22 | no | infeasible | 3 | 1002.62 | 18.09 | yes | worse_vehicles |
| lr205 | 3 | 1054.02 | 3 | 1031.96 | -2.09 | no | infeasible | 5 | 1205.03 | 14.33 | yes | worse_vehicles |
| lr206 | 3 | 931.63 | 8 | 997.41 | 7.06 | no | infeasible | 5 | 1250.65 | 34.24 | yes | worse_vehicles |
| lr207 | 2 | 903.06 | 6 | 851.58 | -5.70 | no | infeasible | 4 | 1106.60 | 22.54 | yes | worse_vehicles |
| lr208 | 2 | 734.85 | 5 | 787.68 | 7.19 | no | infeasible | 3 | 797.99 | 8.59 | yes | worse_vehicles |
| lr209 | 3 | 930.59 | 9 | 944.10 | 1.45 | no | infeasible | 4 | 1100.32 | 18.24 | yes | worse_vehicles |
| lr210 | 3 | 964.22 | 9 | 1014.82 | 5.25 | no | infeasible | 4 | 1038.63 | 7.72 | yes | worse_vehicles |
| lr211 | 2 | 911.52 | 8 | 871.05 | -4.44 | no | infeasible | 4 | 1021.44 | 12.06 | yes | worse_vehicles |
| lrc101 | 14 | 1708.80 | 17 | 1674.01 | -2.04 | no | infeasible | 17 | 1807.84 | 5.80 | yes | worse_vehicles |
| lrc102 | 12 | 1558.07 | 17 | 1602.51 | 2.85 | no | infeasible | 13 | 1619.40 | 3.94 | yes | worse_vehicles |
| lrc103 | 11 | 1258.74 | 14 | 1432.84 | 13.83 | no | infeasible | 12 | 1351.31 | 7.35 | yes | worse_vehicles |
| lrc104 | 10 | 1128.40 | 12 | 1239.32 | 9.83 | no | infeasible | 11 | 1252.98 | 11.04 | yes | worse_vehicles |
| lrc105 | 13 | 1637.62 | 17 | 1632.97 | -0.28 | no | infeasible | 14 | 1649.88 | 0.75 | yes | worse_vehicles |
| lrc106 | 11 | 1424.73 | 15 | 1510.79 | 6.04 | no | infeasible | 14 | 1580.43 | 10.93 | yes | worse_vehicles |
| lrc107 | 11 | 1230.14 | 14 | 1377.20 | 11.95 | no | infeasible | 13 | 1410.99 | 14.70 | yes | worse_vehicles |
| lrc108 | 10 | 1147.43 | 14 | 1320.36 | 15.07 | no | infeasible | 12 | 1372.63 | 19.63 | yes | worse_vehicles |
| lrc201 | 4 | 1406.94 | 11 | 1466.73 | 4.25 | no | infeasible | 7 | 1585.66 | 12.70 | yes | worse_vehicles |
| lrc202 | 3 | 1374.27 | 11 | 1205.14 | -12.31 | no | infeasible | 5 | 1483.96 | 7.98 | yes | worse_vehicles |
| lrc203 | 3 | 1089.07 | 7 | 1010.28 | -7.23 | no | infeasible | 4 | 1251.95 | 14.96 | yes | worse_vehicles |
| lrc204 | 3 | 818.66 | 7 | 929.30 | 13.51 | no | infeasible | 4 | 886.91 | 8.34 | yes | worse_vehicles |
| lrc205 | 4 | 1302.20 | 11 | 1305.34 | 0.24 | no | infeasible | 6 | 1393.39 | 7.00 | yes | worse_vehicles |
| lrc206 | 3 | 1159.03 | 9 | 1181.23 | 1.92 | no | infeasible | 5 | 1230.30 | 6.15 | yes | worse_vehicles |
| lrc207 | 3 | 1062.05 | 8 | 1127.22 | 6.14 | no | infeasible | 4 | 1281.22 | 20.64 | yes | worse_vehicles |
| lrc208 | 3 | 852.76 | 8 | 910.46 | 6.77 | no | infeasible | 4 | 1110.50 | 30.22 | yes | worse_vehicles |

## Aggregate

- Instances compared: 56

### Rust ALNS

- Strict feasible instances: 56 / 56
- Exact matches to reference: 14
- Same vehicle count as reference: 17
- Better vehicle count than reference: 0
- Worse vehicle count than reference: 39
- Average distance gap on strict-feasible cases: 7.73%
- Average distance gap on same-vehicle strict-feasible cases: 0.60%

### PyVRP relaxed model

- Reported feasible instances in the relaxed model: 56 / 56
- Strict feasible instances under Li-Lim evaluation: 5 / 56
- Exact matches to reference: 5
- Same vehicle count as reference on strict-feasible cases: 5
- Better vehicle count than reference on strict-feasible cases: 0
- Worse vehicle count than reference on strict-feasible cases: 0
- Average distance gap on strict-feasible cases: 0.00%
- Average distance gap on same-vehicle strict-feasible cases: 0.00%
