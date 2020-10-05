---
title: Projects
permalink: /projects/
---


<ul>
  {% assign projects_reversed = site.projects | sort: 'date' | reverse %}
  {% for post in projects_reversed %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
      {{ post.excerpt }}
    </li>
  {% endfor %}
</ul>




