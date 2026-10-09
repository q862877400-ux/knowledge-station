# Specification Quality Checklist: 按目录范围提问时，向量通道要真的在范围内找

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-09
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **本仓特有的两条**（不在上游模板里，但本仓规矩要求）：
  - **判据不许放宽**（FR-010）—— 现有那条红用例修好后必须转绿、**断言一字不改**；
    这条写进规格，是为了防"把测试改绿"当成"修好了"。
  - **零回归是硬前提**（FR-004 / SC-002）—— 不限范围的主路径必须逐条不变。
- 规格里**刻意写了三处"读数"**（66 万条、分钟级、逐字节相同）——它们来自**本轮实测**，
  不是估计；plan 阶段要给出复跑命令。
- ⚠ 本规格**没有** [NEEDS CLARIFICATION]：修法与边界都已在 `var/tmp/r18/probe-vec-scope-fix*.py`
  用真机验过（含"只有一种写法成立"这个反直觉结论），没有需要业主拍板的岔路。
