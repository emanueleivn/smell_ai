import { GenerateReportResponse, DetectResponse } from '@/types/types';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
const REQUEST_TIMEOUT = 500000;

const axiosInstance = axios.create({
    baseURL: API_URL,
    timeout: REQUEST_TIMEOUT,
});


// Helper function for consistent error handling
function handleErrorResponse(error: any, fallbackData: any = {}) {
    console.error("API Error:", error.response?.data || error.message || error);
    return fallbackData;
}

// AI-based code smell detection
export async function detectAi(codeSnippet: string): Promise<DetectResponse> {
    try {
        const response = await axiosInstance.post(`${API_URL}/detect_smell_ai`, {
            code_snippet: codeSnippet,
        });

        return {
            success: response.data.success ? response.data.success : false,
            smells: Array.isArray(response.data.smells) ? response.data.smells : [],
        };
    } catch (error) {
        return handleErrorResponse(error, {
            success: false,
            smells: null,
            message: "Error detecting AI-based code smells.",
        });
    }
}

// Static analysis-based code smell detection
export async function detectStatic(codeSnippet: string): Promise<DetectResponse> {
    try {
        const response = await axiosInstance.post(`${API_URL}/detect_smell_static`, {
            code_snippet: codeSnippet,
        });

        return {
            success: response.data.success ? response.data.success : false,
            smells: Array.isArray(response.data.smells) ? response.data.smells : [],
        };

    } catch (error) {
        return handleErrorResponse(error,
            { success: false, smells: null, message: "Error detecting code smells." });
    }
}


// Generate project report
export async function generateReport(projects: any[]): Promise<GenerateReportResponse> {
    try {
        const response = await axiosInstance.post(`${API_URL}/generate_report`, { projects });
        return response.data;
    } catch (error) {
        return handleErrorResponse(error, { report_data: null, message: "Error generating reports." });
    }
}

// Call Graph detection
export async function detectCallGraph(payload: string | File): Promise<any> {
    try {
        if (payload instanceof File) {
            const formData = new FormData();
            formData.append("file", payload);
            formData.append("include_call_graph", "true");

            const response = await axiosInstance.post(`${API_URL}/detect_call_graph`, formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            return response.data;
        } else {
            // String payload
            const response = await axiosInstance.post(`${API_URL}/detect_call_graph`, {
                code_snippet: payload,
                include_call_graph: true
            });
            return response.data;
        }
    } catch (error) {
        return handleErrorResponse(error, {
            success: false,
            smells: [],
            call_graph: null,
            message: "Error detecting call graph."
        });
    }
}
