plt.rcParams["figure.figsize"] = [15.04, 13.39]
fig, axs = plt.subplots(2, 2, constrained_layout=True)
fig.suptitle('Positional Encoding')
ds = [128, 256, 512, 1024]
cs = ['RdBu', 'PuOr', 'BrBG', 'RdYlBu']
for i in range(len(axs.flat)):
    pos_encoding = positional_encoding(2048, ds[i])
    ax = axs.flat[i]
    ax.axis([0, ds[i], 2048, 0])
    ax.set_title(r"$d_{model}$ = " + f"{ds[i]}")
    ax.set(xlabel='Depth', ylabel='Position')
    pcm = ax.pcolormesh(pos_encoding[0], cmap=cs[i])
    fig.colorbar(pcm, ax=ax)