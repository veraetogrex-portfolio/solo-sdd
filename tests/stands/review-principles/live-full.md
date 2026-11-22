=== REVIEW.md
# Review rules

## Rules

1. Never catch a bare `except:`; name the exception. - [#1](https://github.com/example/shop/pull/1#discussion_r101), [#2](https://github.com/example/shop/pull/2#discussion_r104)
2. Every function that opens a file uses `with`. - [#1](https://github.com/example/shop/pull/1), [#4](https://github.com/example/shop/pull/4#discussion_r108)
3. Every money amount is kept in integer cents, never a float. - [#3](https://github.com/example/shop/pull/3#discussion_r107)
4. Every expired coupon is refused with an error, never ignored silently. - solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:13
5. Every refund is logged with its order id. - solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:12
6. A refund never exceeds the paid amount. - solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13
7. Module 1 keeps its public names in `__all__`. - [#21](https://github.com/example/shop/pull/21)
8. Module 2 keeps its public names in `__all__`. - [#22](https://github.com/example/shop/pull/22)
9. Module 3 keeps its public names in `__all__`. - [#23](https://github.com/example/shop/pull/23)
10. Module 4 keeps its public names in `__all__`. - [#24](https://github.com/example/shop/pull/24)
11. Module 5 keeps its public names in `__all__`. - [#25](https://github.com/example/shop/pull/25)
12. Module 6 keeps its public names in `__all__`. - [#26](https://github.com/example/shop/pull/26)
13. Module 7 keeps its public names in `__all__`. - [#27](https://github.com/example/shop/pull/27)
14. Module 8 keeps its public names in `__all__`. - [#28](https://github.com/example/shop/pull/28)
15. Module 9 keeps its public names in `__all__`. - [#29](https://github.com/example/shop/pull/29)
16. Module 10 keeps its public names in `__all__`. - [#30](https://github.com/example/shop/pull/30)
17. Module 11 keeps its public names in `__all__`. - [#31](https://github.com/example/shop/pull/31)
18. Module 12 keeps its public names in `__all__`. - [#32](https://github.com/example/shop/pull/32)
19. Module 13 keeps its public names in `__all__`. - [#33](https://github.com/example/shop/pull/33)
20. Module 14 keeps its public names in `__all__`. - [#34](https://github.com/example/shop/pull/34)
21. Module 15 keeps its public names in `__all__`. - [#35](https://github.com/example/shop/pull/35)
22. Module 16 keeps its public names in `__all__`. - [#36](https://github.com/example/shop/pull/36)
23. Module 17 keeps its public names in `__all__`. - [#37](https://github.com/example/shop/pull/37)
24. Module 18 keeps its public names in `__all__`. - [#38](https://github.com/example/shop/pull/38)
25. Module 19 keeps its public names in `__all__`. - [#39](https://github.com/example/shop/pull/39)

## Unconfirmed

- A function over 15 lines is split. - [#1](https://github.com/example/shop/pull/1#discussion_r102), [#2](https://github.com/example/shop/pull/2#discussion_r103), [#4](https://github.com/example/shop/pull/4#discussion_r110), [#4](https://github.com/example/shop/pull/4#discussion_r111)
=== report
Owner login: shop-owner (AGENTS.md)
Read: PR review comments: 10 remarks, PR reviews: 2 remarks, archive/2026-11-10-add-coupons/verification.md: 2 remarks, archive/2026-11-12-add-refunds/verification.md: 2 remarks
Unread: none
Skipped remarks: 4 by other authors, 0 not review remarks
Rules: 25 in REVIEW.md, 0 new; rules not kept: 1
Unconfirmed: 1 line
The reviewer gets the rules above `## Unconfirmed`; move a line up to confirm it.
