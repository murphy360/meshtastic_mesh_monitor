# Clean Code Review Prompt for Handler Consistency

Use the following prompt to request a comprehensive review of all handler modules before submitting a merge request (MR) or for large-scale project cleanups:

---

**Prompt:**

Please review all handler modules in this project to ensure the following:

1. **Class Pattern Consistency:**
   - All handlers should be implemented as classes inheriting from `BaseHandler`.
   - Each handler should implement an `on_receive` method (or other clearly named entrypoint) with a consistent method signature and usage pattern.

2. **Comment and Docstring Standards:**
   - All class and method docstrings should be present, up-to-date, and follow a consistent format (e.g., Google or NumPy style).
   - Comments should be clear, concise, and reflect the current logic. Remove outdated or misleading comments.

3. **Imports and Dependencies:**
   - Handlers should only import modules and functions that are not already provided by `BaseHandler`.
   - Remove any redundant or unused imports, especially utility imports that are now available via `self.logger`, `self.node_info_utils`, `self.location_utils`, `self.message_sender`, or `self.db_helper`.

4. **General Cleanliness:**
   - Remove any legacy function-based handler code (e.g., `def on_receive_*`) that has been replaced by class-based methods.
   - Ensure code style, spacing, and naming conventions are consistent across all handlers.

5. **Review Output:**
   - Provide a summary of any inconsistencies, outdated comments, or unnecessary imports found.
   - Suggest specific improvements for each handler if needed.

---

Use this prompt as a checklist and guidance for handler code reviews to maintain a clean, maintainable, and professional codebase.
