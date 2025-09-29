
---

**Prompt:**

Please review the entire codebase and provide clean code suggestions that do NOT alter the functional behavior of the code. Focus on the following areas:

1. **Readability & Clarity:**
   - Improve variable, function, and class names for clarity and consistency.
   - Add or update comments and docstrings to explain non-obvious logic.
   - Remove outdated, redundant, or misleading comments.

2. **Code Structure & Organization:**
   - Refactor long functions or classes into smaller, more focused units where appropriate.
   - Ensure consistent code style (indentation, spacing, line length, etc.) throughout the project.
   - Group related functions, classes, and modules logically.

3. **Imports & Dependencies:**
   - Remove unused or redundant imports.
   - Ensure imports are organized and follow project or PEP8 conventions.

4. **Duplication & DRY Principle:**
   - Identify and suggest ways to eliminate code duplication.
   - Recommend utility functions or classes for repeated logic.

5. **Error Handling & Logging:**
   - Ensure exceptions are handled appropriately and consistently.
   - Check that logging is used where needed and follows a consistent pattern.

6. **General Best Practices:**
   - Recommend the use of type hints, f-strings, and other modern Python features where appropriate.
   - Suggest improvements for testability and maintainability.

7. **Review Output:**
   - Provide a summary of key findings and actionable suggestions, organized by file or module.
   - Do not suggest or make changes that would alter the intended behavior of the code.

8. **Review Annotation:**
   - After review, add a comment at the top of every file stating: 
     `# Clean code review: This file was reviewed for clean code standards on YYYY-MM-DD in accordance with standards listed in docs/generic_clean_code_review_prompt.md.`
   - Replace `YYYY-MM-DD` with the actual review date.
# Generic Clean Code Review Prompt

Use this prompt to request a comprehensive clean code review of your entire codebase, focusing on maintainability, readability, and best practices—without changing the functional behavior of your code.

---

**Prompt:**

Please review the entire codebase and provide clean code suggestions that do NOT alter the functional behavior of the code. Focus on the following areas:

1. **Readability & Clarity:**
   - Improve variable, function, and class names for clarity and consistency.
   - Add or update comments and docstrings to explain non-obvious logic.
   - Remove outdated, redundant, or misleading comments.

2. **Code Structure & Organization:**
   - Refactor long functions or classes into smaller, more focused units where appropriate.
   - Ensure consistent code style (indentation, spacing, line length, etc.) throughout the project.
   - Group related functions, classes, and modules logically.

3. **Imports & Dependencies:**
   - Remove unused or redundant imports.
   - Ensure imports are organized and follow project or PEP8 conventions.

4. **Duplication & DRY Principle:**
   - Identify and suggest ways to eliminate code duplication.
   - Recommend utility functions or classes for repeated logic.

5. **Error Handling & Logging:**
   - Ensure exceptions are handled appropriately and consistently.
   - Check that logging is used where needed and follows a consistent pattern.

6. **General Best Practices:**
   - Recommend the use of type hints, f-strings, and other modern Python features where appropriate.
   - Suggest improvements for testability and maintainability.

7. **Review Output:**
   - Provide a summary of key findings and actionable suggestions, organized by file or module.
   - Do not suggest or make changes that would alter the intended behavior of the code.

---

Use this prompt as a checklist and guidance for project-wide clean code reviews to keep your codebase professional, maintainable, and easy to understand.
