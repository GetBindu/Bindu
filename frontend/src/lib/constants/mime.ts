// Centralized MIME allowlists used across client and server
// Keep these lists minimal and consistent with server processing.

export const TEXT_MIME_ALLOWLIST = [
	"text/*",
	"application/json",
	"application/xml",
	"application/csv",
] as const;

export const IMAGE_MIME_ALLOWLIST_DEFAULT = ["image/jpeg", "image/png"] as const;

export const DOCUMENT_MIME_ALLOWLIST = [
	"application/pdf",
	"application/msword",
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	"application/vnd.ms-excel",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	"application/vnd.ms-powerpoint",
	"application/vnd.openxmlformats-officedocument.presentationml.presentation",
	"text/plain",
	"text/csv",
] as const;
