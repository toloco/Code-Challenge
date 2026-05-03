function AppHeader() {
  return (
    <header className="app-header panel">
      <div className="app-header-title-row">
        <svg
          className="app-header-icon"
          viewBox="0 0 64 64"
          role="img"
          aria-label="Cooking pot icon"
        >
          <rect width="64" height="64" rx="14" fill="#fff7ed" />
          <path d="M18 28h28v14c0 6-5 11-11 11h-6c-6 0-11-5-11-11V28z" fill="#c2410c" />
          <path
            d="M22 28v-4c0-2 2-4 4-4h12c2 0 4 2 4 4v4"
            fill="none"
            stroke="#292524"
            strokeWidth="4"
            strokeLinecap="round"
          />
          <path
            d="M46 32h5c3 0 5 2 5 5s-2 5-5 5h-5"
            fill="none"
            stroke="#c2410c"
            strokeWidth="4"
            strokeLinecap="round"
          />
          <path
            className="steam steam-a"
            d="M25 16c-2-3 2-5 0-8"
            fill="none"
            stroke="#6b8f71"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <path
            className="steam steam-b"
            d="M33 16c-2-3 2-5 0-8"
            fill="none"
            stroke="#6b8f71"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <path
            className="steam steam-c"
            d="M41 16c-2-3 2-5 0-8"
            fill="none"
            stroke="#6b8f71"
            strokeWidth="3"
            strokeLinecap="round"
          />
        </svg>
        <div className="app-header-text">
          <h1>Cooking Companion</h1>
          <p className="app-header-subtitle">
            Upload a recipe, then cook step-by-step with your AI assistant.
          </p>
        </div>
      </div>
    </header>
  )
}

export default AppHeader
