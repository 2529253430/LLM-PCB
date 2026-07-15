from pathlib import Path
from src.pcb.route import RoutingResult
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.pcb.board import PCBBoard


class PCBPlacementVisualizer:
    """
    将 PCBBoard 布局结果绘制成图片。
    """

    def save(
        self,
        board: PCBBoard,
        output_path: Path,
        title: str = "LLM-PCB Automatic Placement",
    ) -> Path:
        """
        绘制并保存布局图。
        """

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        figure, axis = plt.subplots(
            figsize=(10, 8)
        )

        self._draw_board(
            axis=axis,
            board=board,
        )

        self._draw_components(
            axis=axis,
            board=board,
        )

        axis.set_title(title)
        axis.set_xlabel(
            f"X Position ({board.unit})"
        )
        axis.set_ylabel(
            f"Y Position ({board.unit})"
        )

        axis.set_xlim(
            -5,
            board.width + 5,
        )
        axis.set_ylim(
            -5,
            board.height + 5,
        )

        axis.set_aspect(
            "equal",
            adjustable="box",
        )
        axis.grid(True)

        figure.tight_layout()

        figure.savefig(
            output_path,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(figure)

        return output_path

    @staticmethod
    def _draw_board(
        axis,
        board: PCBBoard,
    ) -> None:
        """
        绘制 PCB 板框。
        """

        board_outline = Rectangle(
            (0, 0),
            board.width,
            board.height,
            fill=False,
            linewidth=2,
        )

        axis.add_patch(board_outline)

    @staticmethod
    def _draw_components(
        axis,
        board: PCBBoard,
    ) -> None:
        """
        绘制所有元件。
        """

        for component in (
            board.components.values()
        ):
            lower_left_x = (
                component.x
                - component.width / 2
            )
            lower_left_y = (
                component.y
                - component.height / 2
            )

            component_rectangle = Rectangle(
                (
                    lower_left_x,
                    lower_left_y,
                ),
                component.width,
                component.height,
                fill=False,
                linewidth=1.5,
            )

            axis.add_patch(
                component_rectangle
            )

            axis.text(
                component.x,
                component.y,
                (
                    f"{component.reference}\n"
                    f"{component.component_type}"
                ),
                horizontalalignment="center",
                verticalalignment="center",
                fontsize=8,
            )

class PCBRoutingVisualizer:
    """
    绘制 PCB 元件与自动布线路径。
    """

    def save(
        self,
        board: PCBBoard,
        routing_result: RoutingResult,
        output_path: Path,
        title: str = "LLM-PCB Automatic Routing",
    ) -> Path:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        figure, axis = plt.subplots(
            figsize=(10, 8)
        )

        PCBPlacementVisualizer._draw_board(
            axis=axis,
            board=board,
        )

        PCBPlacementVisualizer._draw_components(
            axis=axis,
            board=board,
        )

        self._draw_routes(
            axis=axis,
            routing_result=routing_result,
        )

        axis.set_title(title)
        axis.set_xlabel(
            f"X Position ({board.unit})"
        )
        axis.set_ylabel(
            f"Y Position ({board.unit})"
        )

        axis.set_xlim(
            -5,
            board.width + 5,
        )
        axis.set_ylim(
            -5,
            board.height + 5,
        )

        axis.set_aspect(
            "equal",
            adjustable="box",
        )
        axis.grid(True)

        figure.tight_layout()

        figure.savefig(
            output_path,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(figure)

        return output_path

    @staticmethod
    def _draw_routes(
        axis,
        routing_result: RoutingResult,
    ) -> None:
        """
        绘制全部走线路径。
        """

        for routed_net in (
            routing_result.routed_nets.values()
        ):
            for connection in (
                routed_net.connections
            ):
                x_values = [
                    point.x
                    for point in connection.points
                ]

                y_values = [
                    point.y
                    for point in connection.points
                ]

                axis.plot(
                    x_values,
                    y_values,
                    linewidth=max(
                        routed_net.preferred_width,
                        0.5,
                    ),
                )

                if connection.points:
                    middle_index = (
                        len(connection.points) // 2
                    )

                    label_point = (
                        connection.points[
                            middle_index
                        ]
                    )

                    axis.text(
                        label_point.x,
                        label_point.y,
                        routed_net.net_name,
                        fontsize=7,
                    )