class CryptoManager {
    constructor() {
        // No initialization needed
    }

    async decryptBytesAES(encryptedBytes, password) {
        if (encryptedBytes.length < 28) {
            throw new Error('Invalid encrypted data length. Data is too short.');
        }
        
        const salt = encryptedBytes.slice(0, 16);
        const nonce = encryptedBytes.slice(16, 28);
        const ciphertext = encryptedBytes.slice(28);
        
        // Debug logging
        console.log('[DECRYPTOR:PARAMS] Salt (First 10 bytes HEX):', 
            Array.from(salt.slice(0, 10)).map(b => b.toString(16).padStart(2, '0')).join(''));
        console.log('[DECRYPTOR:PARAMS] Nonce (HEX):', 
            Array.from(nonce).map(b => b.toString(16).padStart(2, '0')).join(''));

        const enc = new TextEncoder();
        const keyMaterial = await crypto.subtle.importKey(
            'raw',
            enc.encode(password),
            { name: 'PBKDF2' },
            false,
            ['deriveKey']
        );

        const key = await crypto.subtle.deriveKey(
            { name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256' },
            keyMaterial,
            { name: 'AES-GCM', length: 256 },
            false,
            ['decrypt']
        );

        const decrypted = await crypto.subtle.decrypt({
            name: 'AES-GCM',
            iv: nonce
        }, key, ciphertext);

        return new Uint8Array(decrypted);
    }

    async openReport(project, suite, date, specificSession = null) {
        if (!window.app?.dashboard?.data) return;
        
        const record = window.app.dashboard.data.data[project]?.[suite]?.[date];
        if (!record) return;
        
        // Use specific session if provided, otherwise use latest
        const session = specificSession || record.latest;
        if (!session || !session.html_file) return;
        
        const password = sessionStorage.getItem('reportPassword');
        if (!password) {
            alert('Password missing!');
            return;
        }

        try {
            // Fetch the encrypted file
            const resp = await fetch(session.html_file);
            if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
            const base64Data = await resp.text();
            
            console.log('[FETCH:OUTPUT] Base64 Data Length:', base64Data.length);
            console.log('[FETCH:OUTPUT] Base64 Data Start:', base64Data.substring(0, 50));
            
            // Decode base64 to get raw binary string
            const binaryString = atob(base64Data);
            
            // Convert binary string to encrypted bytes
            const encryptedBytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                encryptedBytes[i] = binaryString.charCodeAt(i);
            }
            
            // Decrypt the bytes
            const decryptedBytes = await this.decryptBytesAES(encryptedBytes, password);
            
            // Create and open the HTML report
            const decryptedText = new TextDecoder().decode(decryptedBytes);
            const blob = new Blob([decryptedText], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
            
        } catch (error) {
            console.error('Failed to decrypt report:', error);
            this.handleDecryptionError(error);
        }
    }

    handleDecryptionError(error) {
        let message = 'Failed to decrypt report. The password may be incorrect or the data is corrupt.';
        
        if (error.name === 'OperationError') {
            message = 'Decryption failed: Check your password or the report data is tampered.';
        }
        
        alert(message + ' Check the browser console for details (F12).');
    }
}
