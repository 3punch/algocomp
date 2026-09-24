# Algorithm comparison: Fibonacci (naive recursion) vs Fibonacci (memoisation / bottom-up)

> **Task:** compute the n-th Fibonacci number  ·  **Family:** dynamic programming


**Warnings**

- space/average is not declared for Fibonacci (naive recursion); its worst-case bound (O(n)) is used as a conservative stand-in.


## Conclusion

For average-case time, Fibonacci (memoisation / bottom-up) (O(n)) beats Fibonacci (naive recursion) (O(1.618^n)). Fibonacci (memoisation / bottom-up) is better at every input size, not just asymptotically.

**Overall winner: Fibonacci (memoisation / bottom-up)** (weighted score A=0 vs B=6.5)


## Complexity profiles

| | Fibonacci (naive recursion) | Fibonacci (memoisation / bottom-up) |
|---|---|---|
| **category** | dynamic programming | dynamic programming |
| **task** | compute the n-th Fibonacci number | compute the n-th Fibonacci number |
| **time best** | O(1.618^n) | O(n) |
| **time average** | O(1.618^n) | O(n) |
| **time worst** | O(2^n) | O(n) |
| **space worst** | O(n) | O(n) |
| **input sensitive** | yes — best/average/worst differ | — |
| **space average** | — | O(1) |

## Case-by-case verdict

| dimension | case | Fibonacci (naive recursion) | Fibonacci (memoisation / bottom-up) | winner | A÷B as n→∞ | crossover n |
|---|---|---|---|---|---|---|
| time | best | `O(1.618^n)` | `O(n)` | **Fibonacci (memoisation / bottom-up)** | A/B → ∞ (explosive) | — |
| time | average | `O(1.618^n)` | `O(n)` | **Fibonacci (memoisation / bottom-up)** | A/B → ∞ (explosive) | — |
| time | worst | `O(2^n)` | `O(n)` | **Fibonacci (memoisation / bottom-up)** | A/B → ∞ (explosive) | — |
| space | average | `O(n)` | `O(1)` | **Fibonacci (memoisation / bottom-up)** | A/B → ∞ (≈ n^1.00) | — |
| space | worst | `O(n)` | `O(n)` | **tie** | equal | — |

## Growth of the operation count (time/average case)

| n | Fibonacci (naive recursion) `O(1.618^n)` | Fibonacci (memoisation / bottom-up) `O(n)` | A ÷ B | cheaper |
|---|---|---|---|---|
| 10 | 123 | 10 | 12.3 | B |
| 100 | 7.90e+20 | 100 | 7,904,087,286,752,995,328 | B |
| 1,000 | ∞ | 1e+03 | ∞ | B |
| 10,000 | ∞ | 1e+04 | ∞ | B |
| 100,000 | ∞ | 1e+05 | ∞ | B |
| 1,000,000 | ∞ | 1e+06 | ∞ | B |
| 10,000,000 | ∞ | 1e+07 | ∞ | B |
| 1,000,000,000 | ∞ | 1e+09 | ∞ | B |

*Values are the declared growth functions evaluated at n — they count abstract operations, not seconds.*


## Reasoning

- time/best: Fibonacci (naive recursion) O(1.618^n) vs Fibonacci (memoisation / bottom-up) O(n) → Fibonacci (memoisation / bottom-up) is asymptotically better. Fibonacci (naive recursion) is explosive (exponential/factorial) while Fibonacci (memoisation / bottom-up) is not, so the advantage widens without bound.
- time/average: Fibonacci (naive recursion) O(1.618^n) vs Fibonacci (memoisation / bottom-up) O(n) → Fibonacci (memoisation / bottom-up) is asymptotically better. Fibonacci (naive recursion) is explosive (exponential/factorial) while Fibonacci (memoisation / bottom-up) is not, so the advantage widens without bound.
- time/worst: Fibonacci (naive recursion) O(2^n) vs Fibonacci (memoisation / bottom-up) O(n) → Fibonacci (memoisation / bottom-up) is asymptotically better. Fibonacci (naive recursion) is explosive (exponential/factorial) while Fibonacci (memoisation / bottom-up) is not, so the advantage widens without bound.
- space/average: Fibonacci (naive recursion) O(n) vs Fibonacci (memoisation / bottom-up) O(1) → Fibonacci (memoisation / bottom-up) is asymptotically better. the cost ratio grows like n^1.00, so the advantage widens without bound as n grows.
- space/worst: Fibonacci (naive recursion) O(n) vs Fibonacci (memoisation / bottom-up) O(n) → asymptotically equivalent (same growth class).

## Growth classes

| case | Fibonacci (naive recursion) | class | growth exponent | Fibonacci (memoisation / bottom-up) | class | growth exponent |
|---|---|---|---|---|---|---|
| time/best | `O(1.618^n)` | exponential | ∞ | `O(n)` | linear | 1 |
| time/average | `O(1.618^n)` | exponential | ∞ | `O(n)` | linear | 1 |
| time/worst | `O(2^n)` | exponential | ∞ | `O(n)` | linear | 1 |
| space/average | `O(n)` | linear | 1 | `O(1)` | constant | 0 |
| space/worst | `O(n)` | linear | 1 | `O(n)` | linear | 1 |

*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and 10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, ≫2 exponential/factorial.*


## Growth chart (log-log, ASCII)

```text
  3.1e+22 │                                                                            
          │                                                                          AA
          │                                                                    AAAAAA  
          │                                                               AAAAAA       
  1.1e+17 │                                                         AAAAAA             
          │                                                    AAAAAA                  
          │                                              AAAAAA                        
          │                                         AAAAAA                             
  4.2e+11 │                                    AAAAA                                   
          │                              AAAAAA                                        
          │                         AAAAAA                                             
          │                   AAAAAA                                                   
  1.6e+06 │              AAAAAA                                                        
          │        AAAAAA                                                              
          │   AAAAAA                                                                   
          │AAA                               BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
  5.8e+00 │BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB                                          
          │                                                                            
          └────────────────────────────────────────────────────────────────────────────
           10   ← n
  A = O(1.618^n)   B = O(n)   X = the two curves cross/coincide here
  (time/average case · both axes log-scaled · y = operations)
```

## Caveats & constant factors

- **Fibonacci (naive recursion):** The canonical example of exponential blow-up from overlapping subproblems: Θ(φⁿ) ≈ Θ(1.618ⁿ) calls.
- **Fibonacci (memoisation / bottom-up):** Space reduces to O(1) keeping only the last two values. Fast doubling gives O(log n) arithmetic steps (but numbers have O(n) bits, so bit complexity is higher).

---

*Theoretical comparison generated by `algo-compare`. Big-O notation hides constant factors, memory-hierarchy effects and allocation cost — always confirm with an empirical benchmark (`algo-compare verify`) before making a production decision.*
