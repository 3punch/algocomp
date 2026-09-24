# Algorithm comparison: Argon2id vs PBKDF2

> **Task:** derive a key from a password  ·  **Family:** cryptography / hashing


**Warnings**

- The two bounds use different parameters (Argon2id: ['c', 'm'], PBKDF2: ['c', 'n']). Numeric samples below assume every non-`n` parameter equals n, so read them as shape comparisons, not exact values.


## Conclusion

Argon2id and PBKDF2 are in the same asymptotic class for average-case time (O(c·m)). Any real difference comes from constant factors, cache behaviour and allocation — measure before choosing.

**Overall winner: Neither (tie)** (tie on every dimension)


## Complexity profiles

| | Argon2id | PBKDF2 |
|---|---|---|
| **category** | cryptography / hashing | cryptography / hashing |
| **task** | derive a key from a password | derive a key from a password |
| **time best** | O(c·m) | O(c·n) |
| **time average** | O(c·m) | O(c·n) |
| **time worst** | O(c·m) | O(c·n) |
| **space worst** | O(m) | O(n) |

## Case-by-case verdict

| dimension | case | Argon2id | PBKDF2 | winner | A÷B as n→∞ | crossover n |
|---|---|---|---|---|---|---|
| time | best | `O(c·m)` | `O(c·n)` | **tie** | equal | — |
| time | average | `O(c·m)` | `O(c·n)` | **tie** | equal | — |
| time | worst | `O(c·m)` | `O(c·n)` | **tie** | equal | — |
| space | worst | `O(m)` | `O(n)` | **tie** | equal | — |

## Growth of the operation count (time/average case)

| n | Argon2id `O(c·m)` | PBKDF2 `O(c·n)` | A ÷ B | cheaper |
|---|---|---|---|---|
| 10 | 100 | 100 | 1 | = |
| 100 | 1e+04 | 1e+04 | 1 | = |
| 1,000 | 1e+06 | 1e+06 | 1 | = |
| 10,000 | 1e+08 | 1e+08 | 1 | = |
| 100,000 | 1e+10 | 1e+10 | 1 | = |
| 1,000,000 | 1.00e+12 | 1.00e+12 | 1 | = |
| 10,000,000 | 1.00e+14 | 1.00e+14 | 1 | = |
| 1,000,000,000 | 1.00e+18 | 1.00e+18 | 1 | = |

*Values are the declared growth functions evaluated at n — they count abstract operations, not seconds.*


## Reasoning

- time/best: Argon2id O(c·m) vs PBKDF2 O(c·n) → asymptotically equivalent (same growth class).
- time/average: Argon2id O(c·m) vs PBKDF2 O(c·n) → asymptotically equivalent (same growth class).
- time/worst: Argon2id O(c·m) vs PBKDF2 O(c·n) → asymptotically equivalent (same growth class).
- space/worst: Argon2id O(m) vs PBKDF2 O(n) → asymptotically equivalent (same growth class).

## Growth classes

| case | Argon2id | class | growth exponent | PBKDF2 | class | growth exponent |
|---|---|---|---|---|---|---|
| time/best | `O(c·m)` | polynomial (degree ≈ 2.00) | 2 | `O(c·n)` | polynomial (degree ≈ 2.00) | 2 |
| time/average | `O(c·m)` | polynomial (degree ≈ 2.00) | 2 | `O(c·n)` | polynomial (degree ≈ 2.00) | 2 |
| time/worst | `O(c·m)` | polynomial (degree ≈ 2.00) | 2 | `O(c·n)` | polynomial (degree ≈ 2.00) | 2 |
| space/worst | `O(m)` | linear | 1 | `O(n)` | linear | 1 |

*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and 10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, ≫2 exponential/factorial.*


## Growth chart (log-log, ASCII)

```text
  1.9e+19 │                                                                            
          │                                                                          XX
          │                                                                     XXXXX  
          │                                                               XXXXXX       
  8.2e+14 │                                                          XXXXXX            
          │                                                     XXXXXX                 
          │                                                XXXXXX                      
          │                                           XXXXX                            
  3.5e+10 │                                      XXXXX                                 
          │                                 XXXXXX                                     
          │                            XXXXX                                           
          │                      XXXXXX                                                
  1.5e+06 │                 XXXXXX                                                     
          │            XXXXXX                                                          
          │       XXXXXX                                                               
          │  XXXXX                                                                     
  6.5e+01 │XX                                                                          
          │                                                                            
          └────────────────────────────────────────────────────────────────────────────
           10       100       1,000    10,000    100,000           10,000,000   ← n
  A = O(c·m)   B = O(c·n)   X = the two curves cross/coincide here
  (time/average case · both axes log-scaled · y = operations)
```

## Caveats & constant factors

- **Argon2id:** m = memory in KiB (memory-hard by design), c = passes. Resists ASIC/GPU attacks precisely because of the O(m) memory requirement.
- **PBKDF2:** c = iteration count (deliberately huge). Slowness is a *feature* here; it is still fast on GPUs, hence Argon2/scrypt.

---

*Theoretical comparison generated by `algo-compare`. Big-O notation hides constant factors, memory-hierarchy effects and allocation cost — always confirm with an empirical benchmark (`algo-compare verify`) before making a production decision.*
