const html = window.htm.bind(window.React.createElement);

function SvgIcon({ size = 18, children }) {
  return html`
    <svg
      width=${size}
      height=${size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      ${children}
    </svg>
  `;
}

export function LeafMarkIcon() {
  return html`
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M5 19c0-9 6-14 14-14 0 9-6 14-14 14Z" />
      <path d="M5 19l9-9" />
    </svg>
  `;
}

export function ScanIcon() {
  return html`<${SvgIcon}><path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" /><path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" /><path d="M7 12h10" /><//>`;
}

export function ConfirmIcon() {
  return html`<${SvgIcon}><path d="M9 11l3 3 8-8" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /><//>`;
}

export function ClockIcon() {
  return html`<${SvgIcon}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /><//>`;
}

export function ActivityIcon() {
  return html`<${SvgIcon}><path d="M3 12h4l3-7 4 14 3-7h4" /><//>`;
}

export function QrIcon() {
  return html`<${SvgIcon}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><path d="M14 14h3v3h-3z" /><path d="M18 18h3v3h-3z" /><path d="M14 20h1" /><path d="M20 14v1" /><//>`;
}

export function VolumeIcon() {
  return html`<${SvgIcon}><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><path d="M15.5 8.5a5 5 0 0 1 0 7" /><path d="M18.5 5.5a9 9 0 0 1 0 13" /><//>`;
}

export function PauseIcon() {
  return html`<${SvgIcon}><rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" /><//>`;
}

export function SearchIcon() {
  return html`<${SvgIcon}><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /><//>`;
}

export function AlertIcon() {
  return html`<${SvgIcon}><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4" /><path d="M12 17h.01" /><//>`;
}

export function ShieldIcon() {
  return html`<${SvgIcon}><path d="M12 2l7 4v6c0 5-3.5 9-7 10-3.5-1-7-5-7-10V6l7-4z" /><path d="M9 12l2 2 4-4" /><//>`;
}

export function PrintIcon() {
  return html`<${SvgIcon}><path d="M6 9V2h12v7" /><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" /><rect x="6" y="14" width="12" height="8" rx="1" /><//>`;
}

export function DownloadIcon() {
  return html`<${SvgIcon}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M7 10l5 5 5-5" /><path d="M12 15V3" /><//>`;
}

export function TypeSizeIcon() {
  return html`<${SvgIcon}><path d="M4 7V5h12v2" /><path d="M10 5v14" /><path d="M7 19h6" /><path d="M16 12h6" /><path d="M19 9v6" /><//>`;
}

export function PackageIcon() {
  return html`<${SvgIcon}><path d="M16.5 9.4l-9-5.19" /><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /><//>`;
}

export function VideoIcon() {
  return html`<${SvgIcon}><polygon points="23 7 16 12 23 17 23 7" /><rect x="1" y="5" width="15" height="14" rx="2" /><//>`;
}

export function BellIcon() {
  return html`<${SvgIcon}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /><//>`;
}

export function ExternalLinkIcon() {
  return html`<${SvgIcon}><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /><//>`;
}

export function CloseIcon() {
  return html`<${SvgIcon}><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /><//>`;
}
