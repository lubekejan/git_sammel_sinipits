import numpy as np
import vsketch


class Art1Sketch(vsketch.SketchClass):
    # Sketch parameters:
    # radius = vsketch.Param(2.0)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("a3", landscape=False)
        vsk.scale("cm")

        allColumnsPoints = []
        for row in range(20):
            columnPoints = []
            for col in range(25):
                x = row + vsk.random(1.5)
                y = col + vsk.random(1)
                columnPoints.append((x, y))
            allColumnsPoints.append(columnPoints)

        for index in range(len(allColumnsPoints) - 1):
            currentColumnPoints = allColumnsPoints[index]
            nextColumnPoints = allColumnsPoints[index + 1]

            currentColumnPointsUnzipped = zip(*currentColumnPoints)
            currentColumnPointsUnzipped = list(currentColumnPointsUnzipped)
            xTuples = currentColumnPointsUnzipped[0]
            yTuples = currentColumnPointsUnzipped[1]
            xCoordinatesCurrentColumn = np.array(xTuples)
            yCoordinatesCurrentColumn = np.array(yTuples)

            nextColumnPointsUnzipped = zip(*nextColumnPoints)
            nextColumnPointsUnzipped = list(nextColumnPointsUnzipped)
            xTuples = nextColumnPointsUnzipped[0]
            yTuples = nextColumnPointsUnzipped[1]
            xCoordinatesNextColumn = np.array(xTuples)
            yCoordinatesNextColumn = np.array(yTuples)

            interpolation_steps = 9
            for interpolation_step in range(interpolation_steps):
                interpolated_x = vsk.lerp(
                    xCoordinatesCurrentColumn,
                    xCoordinatesNextColumn,
                    interpolation_step / interpolation_steps,
                )
                interpolated_y = vsk.lerp(
                    yCoordinatesCurrentColumn,
                    yCoordinatesNextColumn,
                    interpolation_step / interpolation_steps,
                )
                interpolated_coordinates = zip(interpolated_x, interpolated_y)
                vsk.polygon(interpolated_coordinates)

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")


if __name__ == "__main__":
    Art1Sketch.display()
