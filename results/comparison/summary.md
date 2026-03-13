# Comparison summary

| Instance | PyVRP | Rust | Gap % | PyVRP routes | Rust routes |
| --- | ---: | ---: | ---: | ---: | ---: |
| instance_01 | 357 | 395 | 10.64 | 11 | 11 |
| instance_02 | 470 | 505 | 7.45 | 11 | 11 |
| instance_03 | 460 | 491 | 6.74 | 10 | 10 |
| instance_04 | 395 | 445 | 12.66 | 11 | 11 |
| instance_05 | 553 | 601 | 8.68 | 10 | 10 |
| instance_06 | 414 | 445 | 7.49 | 11 | 11 |
| instance_07 | 410 | 486 | 18.54 | 11 | 10 |
| instance_08 | 320 | 401 | 25.31 | 10 | 10 |
| instance_09 | 443 | 563 | 27.09 | 10 | 11 |
| instance_10 | 402 | 431 | 7.21 | 10 | 10 |

## Aggregate

- PyVRP feasible instances: 10 / 10
- Rust feasible instances: 10 / 10
- Average Rust gap vs PyVRP: 13.18%
- Best Rust gap vs PyVRP: 6.74%
- Worst Rust gap vs PyVRP: 27.09%
