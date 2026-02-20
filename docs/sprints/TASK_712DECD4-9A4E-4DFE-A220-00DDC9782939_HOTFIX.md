# Hotfix Notes: TASK_712DECD4-9A4E-4DFE-A220-00DDC9782939

## Title
Visual hierarchy for nested projects in ProjectsWorkspace list.

## Goal
Make parent/child structure obvious after drag&drop reparenting.

## Implemented
1. Added model roles:
- `ProjectRoles.Depth`
- `ProjectRoles.HasChildren`

2. Built hierarchy caches in model rebuild:
- project depth by parent chain,
- has-children flags by reverse parent map.

3. Updated list rendering:
- indentation by depth,
- node marker before title:
  - `▸` for project with children,
  - `•` for leaf project.

4. Title rendering:
- row title now uses plain project title (without full path),
- hierarchy is represented visually by indent + marker.

## Validation
1. `python -m compileall mindnavigator/workspaces/projects_workspace.py` passed.
