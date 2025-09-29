# Handler Base Class Consistency Review Prompt

Use this prompt to review all handler modules for proper use of the BaseHandler pattern and utility access:

---

**Prompt:**

Please review all handler modules in this project to ensure the following:

1. **BaseHandler Inheritance:**
   - Every handler must inherit from `BaseHandler`.
   - All utility access (logger, node_info_utils, location_utils, message_sender, db_helper) should use `self.` attributes provided by `BaseHandler`.

2. **Imports:**
   - Handlers should NOT import or instantiate utilities (e.g., `get_logger`, `MessageSender`, `lookup_node`, etc.) that are already provided by `BaseHandler`.
   - Remove any redundant or unused imports.

3. **Method Consistency:**
   - The main entrypoint should be an `on_receive` method with a consistent signature.
   - No legacy function-based handler code (e.g., `def on_receive_*`) should remain.

4. **General Cleanliness:**
   - Ensure indentation, code style, and comments are consistent and up to date.

5. **Review Output:**
   - List any handlers that do not follow these patterns and specify what needs to be fixed.

---

Use this prompt as a checklist for handler code reviews to maintain a clean, maintainable, and professional codebase.
