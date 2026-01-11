#!/usr/bin/env python3
"""Generate HTML files from cooklang recipes."""

import json
import subprocess
from pathlib import Path

COOK_CLI = Path.home() / ".cargo/bin/cook"
RECIPES_DIR = Path(__file__).parent

CSS = """
body { font-family: system-ui, sans-serif; max-width: 700px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }
h1 { border-bottom: 2px solid #333; padding-bottom: 0.5rem; }
h2 { color: #555; margin-top: 2rem; }
ul, ol { padding-left: 1.5rem; }
li { margin: 0.5rem 0; }
.ingredient { background: #fef3c7; padding: 0.1rem 0.3rem; border-radius: 3px; }
.cookware { background: #dbeafe; padding: 0.1rem 0.3rem; border-radius: 3px; }
.timer { background: #dcfce7; padding: 0.1rem 0.3rem; border-radius: 3px; }
a { color: #2563eb; }
"""


def get_quantity_str(qty):
    """Extract quantity string from quantity object."""
    if not qty or not qty.get("value"):
        return ""
    val = qty["value"]
    if val.get("type") == "text":
        return val.get("value", "")
    elif val.get("type") == "number":
        num = val.get("value", {})
        if isinstance(num, dict):
            n = num.get("value", "")
        else:
            n = num
        # Format as int if whole number
        return str(int(n)) if isinstance(n, float) and n.is_integer() else str(n)
    return ""


def render_step(step, ingredients, cookware, timers):
    """Render a step with inline ingredients, cookware, and timers."""
    parts = []
    for item in step.get("items", []):
        if item["type"] == "text":
            parts.append(item["value"])
        elif item["type"] == "ingredient":
            ing = ingredients[item["index"]]
            qty = get_quantity_str(ing.get("quantity", {}))
            unit = ing.get("quantity", {}).get("unit", "") or ""
            qty_str = f" ({qty}{' ' + unit if unit else ''})" if qty else ""
            parts.append(f'<span class="ingredient">{ing["name"]}{qty_str}</span>')
        elif item["type"] == "cookware":
            cw = cookware[item["index"]]
            parts.append(f'<span class="cookware">{cw["name"]}</span>')
        elif item["type"] == "timer":
            tm = timers[item["index"]]
            qty = get_quantity_str(tm.get("quantity", {}))
            unit = tm.get("quantity", {}).get("unit", "") or ""
            parts.append(f'<span class="timer">{qty} {unit}</span>')
    return "".join(parts)


def generate_recipe_html(cook_file: Path) -> str:
    """Generate HTML for a single recipe."""
    result = subprocess.run(
        [COOK_CLI, "recipe", str(cook_file), "-f", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)

    title = data.get("metadata", {}).get("map", {}).get("title", cook_file.stem)
    ingredients = data.get("ingredients", [])
    cookware = data.get("cookware", [])
    timers = data.get("timers", [])
    sections = data.get("sections", [])

    # Build ingredients list
    ing_items = []
    for ing in ingredients:
        qty = get_quantity_str(ing.get("quantity", {}))
        unit = ing.get("quantity", {}).get("unit", "") or ""
        qty_str = f": {qty}{' ' + unit if unit else ''}" if qty else ""
        ing_items.append(f"<li>{ing['name']}{qty_str}</li>")

    # Build cookware list
    cw_items = [f"<li>{cw['name']}</li>" for cw in cookware]

    # Build steps
    step_items = []
    for section in sections:
        for item in section.get("content", []):
            if item.get("type") == "step":
                step_html = render_step(item["value"], ingredients, cookware, timers)
                step_items.append(f"<li>{step_html}</li>")

    cookware_section = ""
    if cw_items:
        cookware_section = f"<h2>Cookware</h2>\n<ul>\n{''.join(cw_items)}\n</ul>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body>
  <p><a href="index.html">&larr; All recipes</a></p>
  <h1>{title}</h1>
  <h2>Ingredients</h2>
  <ul>
{"".join(ing_items)}
  </ul>
  {cookware_section}
  <h2>Steps</h2>
  <ol>
{"".join(step_items)}
  </ol>
</body>
</html>"""


def generate_index(recipes: list[tuple[str, str]]) -> str:
    """Generate index.html with links to all recipes."""
    items = [f'<li><a href="{html}">{title}</a></li>' for title, html in recipes]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Recipes</title>
  <style>{CSS}</style>
</head>
<body>
  <h1>Recipes</h1>
  <ul>
{"".join(items)}
  </ul>
</body>
</html>"""


def main():
    recipes = []
    for cook_file in sorted(RECIPES_DIR.glob("*.cook")):
        html_file = cook_file.with_suffix(".html")
        print(f"Generating {html_file.name}...")
        html = generate_recipe_html(cook_file)
        html_file.write_text(html)

        # Extract title for index
        result = subprocess.run(
            [COOK_CLI, "recipe", str(cook_file), "-f", "json"],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        title = data.get("metadata", {}).get("map", {}).get("title", cook_file.stem)
        recipes.append((title, html_file.name))

    # Generate index
    print("Generating index.html...")
    index_html = generate_index(recipes)
    (RECIPES_DIR / "index.html").write_text(index_html)
    print("Done!")


if __name__ == "__main__":
    main()
