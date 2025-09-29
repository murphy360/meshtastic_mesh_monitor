# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.

---

**Prompt:**

This prompt guides a comprehensive clean code review for your codebase, focusing on maintainability, readability, and best practices—without changing functional behavior.

---

**Instructions:**

Review the entire codebase and automatically make clean code changes that do NOT alter functional behavior. For each file:

1. **Readability & Clarity:**
   - Use clear, consistent names for variables, functions, and classes.
   - Add/update comments and docstrings for non-obvious logic.
   - Remove outdated, redundant, or misleading comments.

2. **Structure & Organization:**
   - Refactor long functions/classes into focused units.
   - Ensure consistent code style (indentation, spacing, line length, etc.) and logical grouping.

3. **Imports & Dependencies:**
   - Remove unused/redundant imports; organize per PEP8.

4. **Duplication & DRY Principle:**
   - Eliminate code duplication; use utility functions/classes for repeated logic.
   - This project utilizes several singletons.  Verify if they are correctly leveraged. 

5. **Error Handling & Logging:**
   - Handle exceptions appropriately; use consistent logging.
   - Check that logging is used where needed and follows a consistent pattern. (app\utils\logger.py)

6. **Best Practices:**
   - Use type hints, f-strings, and modern Python features.
   - Improve testability and maintainability.

7. **File Hygiene:**
   - Add TODO at the top of empty files recommending deletion.
   - Add TODO at the top of potentially unused files recommending review for deprecation/removal.
   - Add TODO at the top of files that are not located in correct directories. 

8. **Documentation:**
   - Ensure a top-level README explains project structure, build, test, and deploy.
   - Consolidate documentation files to avoid duplication and outdated information.
   - The `docs` folder should be used to support LLM-based development and temporary files for designing and implementing specific features.
   - Make recommendations to merge duplicate documentation 
   - Make recommendations to delete outdated documentation. 
   - Add TODOs to docs/README files that are outdated, duplicated, or missing info.

9. **Actionable TODOs:**
   - Add TODO comments in relevant sections for recommended changes.

10. **Review Annotation:**
    - Add/update at the top of every file:
        `# YYYY-MM-DD: Clean code review: This file was reviewed for clean code standards.`
        ` # in accordance with standards listed in docs/generic_clean_code_review_prompt.md.`
    - Use the actual review date.

11. **Review Output:**
    - Apply actionable suggestions and provide a summary of key findings by file/module with TODO comments.
    - Do not change intended code behavior.