---
layout: default
title: UnTexed
parent: Works
has_children: true
nav_order: 6
---

# Handwritten notes yet to be TeXed.

{% assign pdf_files = site.static_files | where_exp: "item", "item.path contains '/untexed/'" | sort: "path" %}

<div class="academic-tree-container">
{% assign last_folder_str = "" %}
{% assign first_folder = true %}

{% for file in pdf_files %}
  {% if file.extname == ".pdf" or file.extname == ".PDF" %}
    
    {% assign current_path_parts = file.path | split: "/" %}
    
    {% assign folder_parts = "" | split: "/" %}
    {% for part in current_path_parts %}
      {% if forloop.index > 2 and forloop.last == false %}
        {% assign folder_parts = folder_parts | push: part %}
      {% endif %}
    {% endfor %}
    
    {% capture current_folder_str %}{{ folder_parts | join: " / " }}{% endcapture %}
    {% if current_folder_str == "" %}{% assign current_folder_str = "General" %}{% endif %}

    {% if current_folder_str != last_folder_str %}
      {% if first_folder == false %}
        </ul>
        </details>
      {% endif %}
      
      <details class="academic-folder">
        <summary class="folder-summary">
          <span class="folder-label">{{ current_folder_str | replace: "_", " " }}</span>
        </summary>
        <ul class="file-list">
      {% assign last_folder_str = current_folder_str %}
      {% assign first_folder = false %}
    {% endif %}

    <li class="file-item">
      <a href="{{ file.path | relative_url }}" target="_blank" class="file-link">
        {{ file.basename }}
      </a>
    </li>

  {% endif %}
{% endfor %}

{% if first_folder == false %}
    </ul>
  </details>
{% endif %}
</div>

<style>
  .academic-tree-container { 
    font-family: "Times New Roman", Times, serif; /* 학술적 느낌을 위한 세리프체 권장 (시스템에 따라 다름) */
    line-height: 1.6;
    max-width: 100%;
    margin: 2rem 0;
    color: #1a1a1a;
  }

  /* 폴더 섹션 */
  .academic-folder {
    margin-bottom: 0.5rem;
    border-bottom: 1px solid #eee;
  }

  /* 폴더 제목 (Summary) */
  .folder-summary {
    padding: 0.75rem 0;
    cursor: pointer;
    list-style: none;
    font-weight: 600;
    font-size: 1.1rem;
    display: flex;
    justify-content:间-between;
    align-items: center;
    color: #2c3e50;
  }

  /* HTML 기본 화살표 제거 (대신 텍스트 우측에 작은 표식 추가 가능) */
  .folder-summary::-webkit-details-marker { display: none; }

  /* 폴더명 앞에 아주 얇은 바(Vertical Bar)로 구분감 주기 */
  .folder-label::before {
    content: "§"; /* 문단 기호로 학술적 느낌 부여 */
    margin-right: 12px;
    color: #999;
    font-weight: normal;
  }

  .academic-folder[open] .folder-summary {
    color: #000;
  }

  /* 파일 리스트 */
  .file-list {
    list-style: none;
    padding: 0 0 1rem 1.5rem; /* 왼쪽 들여쓰기로 계층 표현 */
    margin: 0;
  }

  .file-item {
    margin: 0.4rem 0;
  }

  .file-link {
    text-decoration: none;
    color: #555;
    font-size: 0.95rem;
    border-bottom: 1px transparent;
    transition: all 0.2s;
  }

  .file-link:hover {
    color: #000;
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  /* 모바일 대응 */
  @media (max-width: 600px) {
    .folder-summary { font-size: 1rem; }
    .file-link { font-size: 0.9rem; }
  }
</style>