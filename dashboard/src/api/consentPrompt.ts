/**
 * Bridge between the non-React `request()` function and the React ConsentPromptModal.
 * When a 403 consent_required response is received, `requestConsent()` is called,
 * which triggers the modal. The modal grants consent and resolves the promise,
 * allowing `request()` to retry automatically.
 */

export interface ConsentRequest {
    purposes: string[];
    resolve: () => void;
    reject: (reason?: string) => void;
}

type ConsentListener = (req: ConsentRequest) => void;

let listener: ConsentListener | null = null;

/** Called by ConsentPromptModal on mount to subscribe. */
export function onConsentNeeded(cb: ConsentListener): () => void {
    listener = cb;
    return () => { listener = null; };
}

/** Called by request() when a 403 consent_required is received. */
export function requestConsent(purposes: string[]): Promise<void> {
    if (!listener) {
        return Promise.reject(new Error('Consent is required but no prompt is available.'));
    }
    return new Promise<void>((resolve, reject) => {
        listener!({ purposes, resolve, reject });
    });
}
