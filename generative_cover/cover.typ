
#let config = toml("config.toml")

#set page(
  background: place(
    center,
    image(
      config.pictype.style + ".svg",
      width: 100%,
      height: 100%,
    )
  ),
  width: 426mm + (config.typst.buchruecken_mm * 1mm),  // Klebebindung größe
  height: 154mm,
)

#place(
  right,
  dx: 0%,
  dy: 30%,
  text(
    font: "Candara",
    weight: "light",
    size: (config.typst.size_pt * 1pt),
    fill: rgb(config.colors.black),
    stroke: 0.5pt + rgb(config.colors.bg),
  )[best off 2025]
)
