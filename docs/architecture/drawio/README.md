# Editable Diagram Sources

## Purpose
- Store canonical editable diagram sources in native `draw.io` format.
- Keep these files aligned with the diagram inventory in `docs/architecture/diagrams.md`.

## Conventions
- Use one `.drawio` file per documented diagram or business-flow decomposition item.
- Prefer stable file names that capture the scenario and, when needed, the sheet format, for
  example `hr-user-workflow-a1-sheet.drawio`.
- Update the linked documentation entry in the same task whenever a diagram changes.
- Keep diagrams editable; do not replace the source of truth with a Mermaid import snapshot only.

## Inventory
- `hr-user-workflow-a1-sheet.drawio`: detailed HR user workflow algorithm on an `A1` sheet;
  labels are in Russian and the diagram uses a black-and-white editable `draw.io` layout.
- `application-structure-a1-sheet.drawio`: structural diagram of the whole application on an `A1`
  sheet; labels are in Russian and the diagram uses a black-and-white editable `draw.io` layout.
- `application-use-cases-a1-sheet.drawio`: use case diagram of the whole application on an `A1`
  sheet; labels are in Russian and the diagram uses a black-and-white editable `draw.io` layout
  with more formal UML-like actor associations and `<<extend>>` links.
- `database-structure-a1-sheet.drawio`: database structure diagram of the whole application on an
  `A1` sheet; labels are in Russian and the diagram uses a black-and-white editable `draw.io`
  layout with stricter ERD notation, field types, constraints, and FK/logical-reference links.
