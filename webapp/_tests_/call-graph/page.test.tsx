import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import CallGraphPage from "../../app/call-graph/page";
import * as api from "../../utils/api";

// Mock API
jest.mock("../../utils/api", () => ({
    detectCallGraph: jest.fn(),
}));

// Mock ReactFlow
jest.mock("reactflow", () => ({
    __esModule: true,
    default: ({ nodes, edges, onNodeClick }) => (
        <div data-testid="react-flow-mock">
            {nodes.map((n) => (
                <div
                    key={n.id}
                    data-testid={`node-${n.id}`}
                    onClick={() => onNodeClick && onNodeClick({}, n)}
                >
                    {n.data.label}
                </div>
            ))}
        </div>
    ),
    Background: () => <div />,
    Controls: () => <div />,
    useNodesState: jest.fn((initial) => {
        const [nodes, setNodes] = React.useState(initial);
        return [nodes, setNodes, jest.fn()];
    }),
    useEdgesState: jest.fn((initial) => {
        const [edges, setEdges] = React.useState(initial);
        return [edges, setEdges, jest.fn()];
    }),
    ReactFlowProvider: ({ children }) => <div>{children}</div>
}));

// Mock JSZip
jest.mock("jszip", () => ({
    __esModule: true,
    default: jest.fn().mockImplementation(() => ({
        file: jest.fn(),
        generateAsync: jest.fn().mockResolvedValue(new Blob(["mock zip content"], { type: "application/zip" })),
    })),
}));

// Mock dagre
jest.mock("dagre", () => ({
    graphlib: {
        Graph: jest.fn().mockImplementation(() => ({
            setGraph: jest.fn(),
            setDefaultEdgeLabel: jest.fn(),
            setNode: jest.fn(),
            setEdge: jest.fn(),
            node: jest.fn().mockReturnValue({ x: 0, y: 0 }),
        })),
    },
    layout: jest.fn(),
}));

describe("CallGraphPage", () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it("renders the page title and description", () => {
        render(<CallGraphPage />);
        expect(screen.getByText("Upload File / Project")).toBeInTheDocument();
    });

    it("handles file upload and renders graph", async () => {
        // Mock API response
        const mockGraph = {
            nodes: [
                {
                    id: "1",
                    name: "Main.py",
                    file_path: "Main.py",
                    start_line: 1,
                    end_line: 10,
                    type: "default",
                    data: { label: "Main.py" },
                    position: { x: 0, y: 0 }
                },
                {
                    id: "2",
                    name: "Utils.py",
                    file_path: "Utils.py",
                    start_line: 1,
                    end_line: 5,
                    type: "default",
                    data: { label: "Utils.py" },
                    position: { x: 100, y: 0 }
                },
            ],
            edges: []
        };
        (api.detectCallGraph as jest.Mock).mockResolvedValue({
            success: true,
            call_graph: mockGraph,
            smells: []
        });

        render(<CallGraphPage />);

        // Simulate clicking the upload button
        // Note: We're mocking the hidden file input behavior or the visual button
        // The component has <input type="file" ... />
        const fileInput = screen.getByTestId("file-upload-input");

        // Create a dummy file
        const file = new File(["dummy content"], "project.zip", { type: "application/zip" });

        // Trigger change event
        fireEvent.change(fileInput, { target: { files: [file] } });

        // Click the Generate button
        const generateButton = screen.getByText("Generate Call Graph");
        fireEvent.click(generateButton);

        // Wait for API call
        await waitFor(() => {
            expect(api.detectCallGraph).toHaveBeenCalled();
        });

        // Check if nodes are rendered (by our mock ReactFlow)
        // Check if nodes are rendered (by our mock ReactFlow)
        await screen.findByTestId("node-1");
        expect(screen.getByText(/Main.py/)).toBeInTheDocument();
    });

    it("displays source code modal when node is clicked", async () => {
        // Setup with a node containing source code
        const mockGraph = {
            nodes: [
                {
                    id: "1",
                    name: "Main.py",
                    file_path: "Main.py",
                    start_line: 1,
                    end_line: 5,
                    type: "default",
                    data: { label: "Main.py" },
                    position: { x: 0, y: 0 },
                    source_code: "def main():\n    print('hello')"
                },
            ],
            edges: []
        };
        (api.detectCallGraph as jest.Mock).mockResolvedValue({
            success: true,
            call_graph: mockGraph,
            smells: []
        });

        render(<CallGraphPage />);

        const fileInput = screen.getByTestId("file-upload-input");
        const file = new File(["dummy"], "project.zip", { type: "application/zip" });
        fireEvent.change(fileInput, { target: { files: [file] } });

        // Click the Generate button
        const generateButton = screen.getByText("Generate Call Graph");
        fireEvent.click(generateButton);

        await waitFor(() => expect(api.detectCallGraph).toHaveBeenCalled());

        // Click the node
        const node = screen.getByTestId("node-1");
        fireEvent.click(node);

        // Verify modal content shows up
        expect(screen.getByText("Node: Main.py")).toBeInTheDocument();
        expect(screen.getByText("def main():")).toBeInTheDocument();
    });
});
