
#let buchruecken = 20mm

#set page(
  background: place(
    center,
    image(
      "organic_with_blobs.svg",
      width: 100%,
      height: 100%,
    )
  ),
  width: 426mm + buchruecken,  // Klebebindung größe
  height: 154mm,
)

#place(
  right,
  dx: -5%,
  dy: 20%,
  text(
    font: "0xProto Nerd Font",
    weight: "bold",
    size: 60pt,
    fill: rgb("#000000"),
    stroke: 1pt + rgb("#FFFFFF"),
  )[best off 2025]
)
