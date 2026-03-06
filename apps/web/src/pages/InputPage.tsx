interface InputPageProps {
  company: string;
  website: string;
  token: string;
  rememberToken: boolean;
  loading: boolean;
  error: string | null;
  onCompanyChange: (value: string) => void;
  onWebsiteChange: (value: string) => void;
  onTokenChange: (value: string) => void;
  onRememberTokenChange: (value: boolean) => void;
  onClearToken: () => void;
  onConnect: () => void;
}

export function InputPage({
  company,
  website,
  token,
  rememberToken,
  loading,
  error,
  onCompanyChange,
  onWebsiteChange,
  onTokenChange,
  onRememberTokenChange,
  onClearToken,
  onConnect,
}: InputPageProps) {
  const isValid = company.trim() && website.trim() && token.trim();

  return (
    <div className="card">
      <div className="space-y-5">
        <div>
          <label className="label">Company Name</label>
          <input
            type="text"
            className="input"
            placeholder="e.g., Acme Corporation"
            value={company}
            onChange={(e) => onCompanyChange(e.target.value)}
            disabled={loading}
          />
        </div>

        <div>
          <label className="label">Website URL</label>
          <input
            type="url"
            className="input"
            placeholder="https://acme.com"
            value={website}
            onChange={(e) => onWebsiteChange(e.target.value)}
            disabled={loading}
          />
        </div>

        <div>
          <label className="label">Productboard API Token</label>
          <input
            type="password"
            className="input"
            placeholder="pb_xxx..."
            value={token}
            onChange={(e) => onTokenChange(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-800"
              checked={rememberToken}
              onChange={(e) => onRememberTokenChange(e.target.checked)}
              disabled={loading}
            />
            Remember token on this device
          </label>

          {token && (
            <button
              type="button"
              className="text-sm text-gray-400 hover:text-red-400 transition-colors"
              onClick={onClearToken}
              disabled={loading}
            >
              Clear saved token
            </button>
          )}
        </div>

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        <button
          className="btn btn-primary w-full"
          onClick={onConnect}
          disabled={!isValid || loading}
        >
          {loading ? 'Analyzing...' : 'Analyze Space'}
        </button>
      </div>
    </div>
  );
}
