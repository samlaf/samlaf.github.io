---
title: Blog
permalink: /blog/
---

<ul>
    <!-- site.posts are already ordered by reverse chronology -->
  {% for post in site.posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
      {{ post.excerpt }}
    </li>
  {% endfor %}
</ul>

