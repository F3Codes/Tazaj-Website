from django.contrib.admin.widgets import AdminFileWidget
from django.utils.safestring import mark_safe


class PasteImageWidget(AdminFileWidget):
    """
    A file input that also accepts pasted images from the clipboard.

    Renders the standard Django file input, plus a drop zone above it.
    When the user pastes an image anywhere on the page (or drops a file
    onto the zone), the file gets assigned to the underlying input.
    """

    def render(self, name, value, attrs=None, renderer=None):
        # Render the standard admin file widget first
        base_html = super().render(name, value, attrs, renderer)

        # A unique id so multiple paste widgets on one page don't clash
        widget_id = f"paste-{name}"

        extra_html = f"""
        <div class="paste-image-widget" id="{widget_id}">
            <div class="paste-zone" tabindex="0">
                <div class="paste-zone-icon">📋</div>
                <div class="paste-zone-text">
                    <strong>Paste an image here</strong><br>
                    <span>Press Ctrl+V (⌘+V on Mac) anywhere on the page,
                    or drag &amp; drop a file</span>
                </div>
            </div>
            <img class="paste-preview" alt="Preview" style="display:none;">
        </div>

        <style>
            .paste-image-widget {{
                margin-bottom: 0.75rem;
            }}
            .paste-zone {{
                border: 2px dashed #cbd5e1;
                border-radius: 10px;
                padding: 1rem 1.25rem;
                background: #f8fafc;
                display: flex;
                align-items: center;
                gap: 1rem;
                cursor: pointer;
                transition: all 0.2s;
                max-width: 480px;
            }}
            .paste-zone:hover,
            .paste-zone:focus,
            .paste-zone.active {{
                border-color: #16a34a;
                background: #f0fdf4;
                outline: none;
            }}
            .paste-zone-icon {{
                font-size: 1.5rem;
            }}
            .paste-zone-text {{
                font-size: 0.85rem;
                color: #475569;
                line-height: 1.4;
            }}
            .paste-zone-text strong {{
                color: #0f172a;
            }}
            .paste-preview {{
                display: block;
                max-height: 180px;
                margin-top: 0.75rem;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }}
        </style>

        <script>
        (function() {{
            const container = document.getElementById("{widget_id}");
            const zone = container.querySelector(".paste-zone");
            const preview = container.querySelector(".paste-preview");
            const input = document.getElementById("id_{name}");
            if (!input) return;

            function setFile(file) {{
                if (!file || !file.type.startsWith("image/")) return;

                // Put the file into the input via DataTransfer
                const dt = new DataTransfer();
                dt.items.add(file);
                input.files = dt.files;

                // Preview
                const reader = new FileReader();
                reader.onload = (e) => {{
                    preview.src = e.target.result;
                    preview.style.display = "block";
                }};
                reader.readAsDataURL(file);

                // Visual feedback
                zone.classList.add("active");
                setTimeout(() => zone.classList.remove("active"), 600);
            }}

            // Paste handler (page-wide, but only consumes images)
            document.addEventListener("paste", (e) => {{
                const items = e.clipboardData && e.clipboardData.items;
                if (!items) return;
                for (const item of items) {{
                    if (item.type.startsWith("image/")) {{
                        const file = item.getAsFile();
                        if (file) {{
                            setFile(file);
                            e.preventDefault();
                        }}
                        break;
                    }}
                }}
            }});

            // Click the zone → focus hidden file input as a fallback
            zone.addEventListener("click", () => input.click());

            // Drag & drop
            zone.addEventListener("dragover", (e) => {{
                e.preventDefault();
                zone.classList.add("active");
            }});
            zone.addEventListener("dragleave", () => {{
                zone.classList.remove("active");
            }});
            zone.addEventListener("drop", (e) => {{
                e.preventDefault();
                zone.classList.remove("active");
                if (e.dataTransfer.files.length) {{
                    setFile(e.dataTransfer.files[0]);
                }}
            }});
        }})();
        </script>
        """

        return mark_safe(base_html + extra_html)