import { Link } from 'react-router-dom';

export function LandingPage() {
  return (
    <div className="min-h-screen py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-2xl font-semibold mb-2">Productboard Demo Tools</h1>
          <p className="text-gray-400 text-sm">
            Sales enablement tools for demo preparation
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Insights Generator Card */}
          <div className="card flex flex-col">
            <div className="w-12 h-12 bg-primary-500 rounded-lg flex items-center justify-center mb-4">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-6 h-6 text-white"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            </div>
            <h2 className="text-lg font-semibold mb-2">
              Insights Generator
              <span className="ml-2 px-2 py-0.5 bg-primary-500 text-white text-xs font-semibold uppercase rounded">
                New
              </span>
            </h2>
            <p className="text-gray-400 text-sm flex-grow mb-5">
              Generate realistic customer feedback notes for any company. Add
              5-50 AI-generated insights to your Productboard space.
            </p>
            <Link to="/insights" className="btn btn-primary text-center">
              Open
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-4 h-4 ml-2 inline"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </Link>
          </div>

          {/* Demo Generator Card */}
          <div className="card flex flex-col">
            <div className="w-12 h-12 bg-primary-500 rounded-lg flex items-center justify-center mb-4">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-6 h-6 text-white"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
                />
              </svg>
            </div>
            <h2 className="text-lg font-semibold mb-2">Demo Generator</h2>
            <p className="text-gray-400 text-sm flex-grow mb-5">
              Full POC demo setup. Rename products, components, features, and
              strategic hierarchy to match your prospect's business.
            </p>
            <Link to="/demo-generator" className="btn btn-primary text-center">
              Open
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-4 h-4 ml-2 inline"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
