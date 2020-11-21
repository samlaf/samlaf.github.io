import daft
from matplotlib import rc

rc("font", family="serif", size=12)
rc("text", usetex=True)


pgm = daft.PGM(observed_style="inner")

pgm.add_node("theta", r"$\theta$", 1, 2)
pgm.add_node("Xi", r"$X_i$", 1, 1, observed=True)
pgm.add_node("ht", r'hypothesis testing', 3, 2, plot_params={"ec": "none"})
pgm.add_node("ad", r'anomaly detection', 3, 1, plot_params={"ec": "none"})

# Add in the edges.
pgm.add_edge("theta", "Xi")

# And a plate.
pgm.add_plate([0.5, 0.5, 1, 1])

# Render and save.
pgm.render()
pgm.savefig("pi-x-pgm.pdf", transparent = True, bbox_inches = 'tight', pad_inches = 0)
#pgm.show()