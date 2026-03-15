---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults
---

<!-- "Programming Articles" -->
<h2> <a style="color:#000000" href="blog"> Programming </a> </h2>
<ul>
{% for post in site.posts %}
	{% if post.category == "programming" %}
		<li><a href="{{ post.url }}">{{ post.title }}</a> <span style="color:#888; font-size:0.85em;">({{ post.date | date: "%Y-%m-%d" }})</span></li>
	{% endif %}
{% endfor %}
</ul>

<!-- "Blockchain Articles" -->
<h2> <a style="color:#000000" href="blog"> Blockchain </a> </h2>
<ul>
{% assign blockchain_posts = site.posts | where: "category", "blockchain" %}
<!-- external articles are listed under _data/external_posts -->
{% assign all_posts = blockchain_posts | concat: site.data.external_posts.blockchain | sort: "date" | reverse %}
{% for post in all_posts %}
	<li><a href="{{ post.url }}">{{ post.title }}</a> <span style="color:#888; font-size:0.85em;">({{ post.date | date: "%Y-%m-%d" }})</span></li>
{% endfor %}
</ul>

<!-- "Other Blog Posts"  -->
<h2> <a style="color:#000000" href="blog"> Miscellaneous </a> </h2>
<ul>
{% for post in site.posts %}
	{% if post.category != "blockchain" and post.category != "programming" %}
		<li><a href="{{ post.url }}">{{ post.title }}</a> <span style="color:#888; font-size:0.85em;">({{ post.date | date: "%Y-%m-%d" }})</span></li>
	{% endif %}
{% endfor %}
</ul>

<!-- Presentations / Videos -->
<div class='iconandproject'> 
	<h2> Presentations </h2>
	{% assign presentations = site.presentations | reverse %}
	{% for p in presentations %}
		<div style="clear: left;">
			<img src="/presentations/{{ p.slug }}.png" class='iconDetails'>
		</div>
		<div style='margin-left:150px;'>
			<h4> <a href="{% if p.external_url %}{{ p.external_url }}{% else %}{{ p.url }}{% endif %}">{{ p.title }}</a> </h4>
			<div style="font-size:.6em;"> {{ p.abstract | markdownify}} </div>
		</div>
	{% endfor %}
</div>
