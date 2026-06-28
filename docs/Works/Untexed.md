---
layout: default
title: UnTexed
parent: Works
has_children: true
nav_order: 6
---

# Handwritten notes yet to be TeXed.


{% assign pdf_files = site.static_files | where_exp: "item", "item.path contains '/untexed/'" %}

{% for file in pdf_files %}
  {% if file.extname == ".pdf" %}
* [{{ file.basename }}]({{ file.path | relative_url }}){:target="_blank"}
  {% endif %}
{% endfor %}

---
{: .fs-2 }
