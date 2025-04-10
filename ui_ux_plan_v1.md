# Co-Lab: UI/UX Plan (V1 Mock-up)

This document outlines the plan for creating an initial high-fidelity visual design mock-up for the Co-Lab user interface.

## 1. Goal & Scope

*   **Purpose:** Create a high-fidelity visual design representing the look and feel of the Co-Lab application.
*   **Scope:** Focus on visualizing the core user interactions: submitting prompts, viewing responses, uploading data, and viewing token balance/history.

## 2. Key Screens / Views

The mock-up should include designs for the following primary views:

1.  **Main Interaction View (Chat Interface):**
    *   The central hub for user interaction with the Core AI.
    *   Resembles a modern chat application.
2.  **Data Upload View:**
    *   A dedicated interface for users to contribute data files to the IPFS network.
3.  **Token Wallet / Dashboard View:**
    *   Displays the user's `COLAB` token balance and transaction history.

## 3. Essential Components per View

*   **Main Interaction View:**
    *   Chat History Area (displaying past prompts and responses)
    *   Prompt Input Field (resizable, clear button)
    *   Submit Button
    *   Response Display Area (handling markdown, code blocks)
    *   Processing Status Indicator (e.g., "Thinking...", "Contacting Specialist...", "Synthesizing...")
    *   Estimated/Actual Query Cost Display (in `COLAB`)
    *   Clear Navigation (to Upload, Wallet views)
    *   Global Token Balance (e.g., in header)
*   **Data Upload View:**
    *   File Selector / Drag-and-Drop Zone
    *   Metadata Input Fields:
        *   Filename (read-only, from file)
        *   Description (required text area)
        *   Tags (required input, allows multiple tags, maybe suggestions)
    *   Upload/Submit Button
    *   Progress Indicator (for upload & IPFS pinning)
    *   Confirmation Area (displaying success/failure, generated CID, `COLAB` reward amount)
    *   Navigation back
*   **Token Wallet / Dashboard View:**
    *   Current `COLAB` Balance Display (prominent)
    *   Transaction History List/Table:
        *   Timestamp
        *   Type (e.g., "Query Cost", "Data Reward")
        *   Amount (+/- `COLAB`)
        *   Details (e.g., Prompt snippet, Uploaded CID/Filename)
    *   Navigation back

## 4. Core User Flows

The design should facilitate these primary flows:

*   **Query Flow:** User lands on Interaction View -> Enters prompt -> Submits -> Sees status -> Sees response -> Balance potentially updated.
*   **Upload Flow:** User navigates to Upload View -> Selects file -> Enters metadata -> Submits -> Sees progress -> Sees confirmation -> Balance potentially updated.
*   **Balance Check:** User navigates to Wallet View -> Sees balance and history.

**User Flow Diagram (Mermaid Code):**

```mermaid
graph TD
    subgraph "User Starts"
        Start((Start)) --> MainView{Main Interaction View}
        MainView --> Nav1(Navigate)
        Nav1 --> UploadView{Data Upload View}
        Nav1 --> WalletView{Token Wallet View}
        UploadView --> Nav2(Navigate Back)
        WalletView --> Nav3(Navigate Back)
        Nav2 --> MainView
        Nav3 --> MainView
    end

    subgraph "Query Flow"
        MainView -- 1. Enter Prompt --> PromptInput[Prompt Input]
        PromptInput -- 2. Submit --> CoreAI_API[/core/prompt API Call]
        CoreAI_API -- 3. Processing... --> StatusDisplay(Show Status Updates)
        CoreAI_API -- 4. FinalResponse --> ResponseDisplay[Display Response]
        CoreAI_API -- Cost Info --> WalletView_Update(Update Balance)
        ResponseDisplay --> MainView
    end

    subgraph "Upload Flow"
        UploadView -- 1. Select File/Metadata --> UploadForm[Upload Form]
        UploadForm -- 2. Submit --> Uploader_API[/upload API Call]
        Uploader_API -- 3. Processing... --> UploadProgress(Show Progress)
        Uploader_API -- 4. Confirmation --> UploadConfirm[Display CID & Reward]
        Uploader_API -- Reward Info --> WalletView_Update
        UploadConfirm --> UploadView
    end

```

## 5. Visual Style & Considerations

*   **Aesthetic:** Clean, modern, intuitive, potentially with a "tech" or "data" feel.
*   **Branding:** Incorporate Co-Lab logo and color scheme consistently.
*   **Theme:** Consider both light and dark mode designs.
*   **Transparency:** Use status indicators and clear cost/reward displays to build trust. Avoid overly complex visualizations of the internal AI process initially.
*   **Responsiveness:** While primarily a visual design, consider how layouts might adapt to different screen sizes.

## 6. Next Steps (Implementation)

Based on this plan, the next step is to create the actual high-fidelity mock-ups using design tools (like Figma, Sketch, Adobe XD) or potentially implement a basic HTML/CSS/JS prototype. This would typically be done in Code mode or by a dedicated UI/UX designer.