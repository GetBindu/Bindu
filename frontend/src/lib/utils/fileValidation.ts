/**
 * File upload validation and management utilities
 * Handles validation of file types, sizes, and provides user-friendly error messages
 */

export const FILE_SIZE_LIMIT = 10 * 1024 * 1024; // 10MB
export const FILE_SIZE_LIMIT_DISPLAY = "10MB";

export interface FileValidationResult {
	valid: boolean;
	error?: string;
	file?: File;
}

/**
 * Validate a single file against mime type and size restrictions
 */
export function validateFile(
	file: File,
	allowedMimeTypes: string[] = [],
	maxSize: number = FILE_SIZE_LIMIT
): FileValidationResult {
	// Check file size
	if (file.size > maxSize) {
		const maxSizeDisplay = formatFileSize(maxSize);
		return {
			valid: false,
			error: `File "${file.name}" exceeds maximum size of ${maxSizeDisplay}. Current size: ${formatFileSize(file.size)}.`,
		};
	}

	// Check file type if specifications are provided
	if (allowedMimeTypes.length > 0) {
		const isAllowed = allowedMimeTypes.some((mimeType) => {
			const [allowedType, allowedSubtype] = mimeType.toLowerCase().split("/");
			const [fileType, fileSubtype] = file.type.toLowerCase().split("/");

			return (
				(allowedType === "*" || allowedType === fileType) &&
				(allowedSubtype === "*" || allowedSubtype === fileSubtype)
			);
		});

		if (!isAllowed) {
			const supportedTypes = formatMimeTypes(allowedMimeTypes);
			return {
				valid: false,
				error: `File type "${file.type}" is not supported. Supported types: ${supportedTypes}.`,
			};
		}
	}

	return { valid: true, file };
}

/**
 * Validate multiple files
 */
export function validateFiles(
	files: File[],
	allowedMimeTypes: string[] = [],
	maxSize: number = FILE_SIZE_LIMIT
): { valid: File[]; errors: string[] } {
	const valid: File[] = [];
	const errors: string[] = [];

	for (const file of files) {
		const result = validateFile(file, allowedMimeTypes, maxSize);
		if (result.valid && result.file) {
			valid.push(result.file);
		} else if (result.error) {
			errors.push(result.error);
		}
	}

	return { valid, errors };
}

/**
 * Format file size for user display
 */
export function formatFileSize(bytes: number): string {
	if (bytes === 0) return "0 Bytes";
	const k = 1024;
	const sizes = ["Bytes", "KB", "MB", "GB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * Format mime types for display
 */
export function formatMimeTypes(mimeTypes: string[]): string {
	if (mimeTypes.length === 0) return "All types";

	const typeNames = mimeTypes
		.map((mime) => {
			if (mime === "image/*") return "Images";
			if (mime === "text/*") return "Text files";
			if (mime === "application/pdf") return "PDF";
			if (mime === "application/json") return "JSON";
			if (mime.includes("*")) return mime.replace("/*", " files");
			return mime;
		})
		.filter((v, i, a) => a.indexOf(v) === i); // Remove duplicates

	if (typeNames.length > 3) {
		return typeNames.slice(0, 3).join(", ") + `, and ${typeNames.length - 3} more`;
	}

	return typeNames.join(", ");
}

/**
 * Get human-readable description of allowed file types and size limits
 */
export function getFileUploadConstraints(
	allowedMimeTypes: string[],
	maxSize: number = FILE_SIZE_LIMIT
): string {
	const types = formatMimeTypes(allowedMimeTypes);
	const maxSizeDisplay = formatFileSize(maxSize);
	return `Supported: ${types}. Maximum file size: ${maxSizeDisplay}.`;
}
