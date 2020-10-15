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

<video width="480" height="320" controls="controls">
	<source src="/assets/videos/duckiebots-driving-husky.mp4" type="video/mp4">
</video>