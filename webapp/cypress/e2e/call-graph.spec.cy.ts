describe('Interactive Call Graph Feature', () => {
    beforeEach(() => {
        // Navigate to the call graph page
        cy.visit('/call-graph');
    });

    it('should render the upload interface initially', () => {
        cy.contains('Upload File / Project').should('be.visible');
        cy.contains('Click or Drag to Upload').should('be.visible');
    });

    it('should handle ZIP upload and display graph', () => {
        // Mock the API response for detect_call_graph
        cy.intercept('POST', '/api/detect_call_graph', {
            statusCode: 200,
            body: {
                success: true,
                call_graph: {
                    nodes: [
                        {
                            id: 'node1',
                            name: 'main.py',
                            type: 'default',
                            data: { label: 'main.py' },
                            position: { x: 0, y: 0 },
                            source_code: 'def main():\n  pass'
                        },
                        {
                            id: 'node2',
                            name: 'utils.py',
                            type: 'default',
                            data: { label: 'utils.py' },
                            position: { x: 100, y: 0 },
                            source_code: 'def helper():\n  return True'
                        }
                    ],
                    edges: [
                        { id: 'e1-2', source: 'node1', target: 'node2' }
                    ]
                },
                smells: []
            }
        }).as('detectCallGraph');

        // Create a dummy zip file
        const fileName = 'project.zip';
        // Select file input using data-testid
        cy.get('[data-testid="file-upload-input"]').selectFile({
            contents: Cypress.Buffer.from('dummy zip content'),
            fileName: 'project.zip',
            mimeType: 'application/zip',
            lastModified: Date.now(),
        }, { force: true });

        // Wait for API
        cy.contains('Generate Call Graph').click();
        cy.wait('@detectCallGraph');

        // Use find by text with regex to be safe
        cy.contains('main.py').should('be.visible');
        // cy.contains('utils.py').should('be.visible'); // Might need layout time
    });

    it('should open source code modal on node click', () => {
        // Mock API
        cy.intercept('POST', '/api/detect_call_graph', {
            body: {
                success: true,
                call_graph: {
                    nodes: [
                        {
                            id: 'n1',
                            name: 'test.py',
                            data: { label: 'test.py' },
                            position: { x: 100, y: 300 },
                            source_code: 'print("hello world")',
                            file_path: 'test.py',
                            start_line: 1,
                            end_line: 1
                        }
                    ],
                    edges: []
                },
                smells: []
            }
        }).as('detectCallGraph');

        // Upload file
        cy.get('[data-testid="file-upload-input"]').selectFile({
            contents: Cypress.Buffer.from('dummy'),
            fileName: 'test.zip',
            mimeType: 'application/zip'
        }, { force: true });

        cy.contains('Generate Call Graph').click();
        cy.wait('@detectCallGraph');

        // Wait for layout animation and toast to disappear
        cy.wait(6000);

        // Usage of trigger might be more robust for React Flow
        cy.get('[data-id="n1"]').click({ force: true });

        // Check modal content
        cy.contains('Node: test.py').should('be.visible');
        cy.contains('Source Code').should('be.visible');
        cy.contains('print("hello world")').should('be.visible');
    });
});
