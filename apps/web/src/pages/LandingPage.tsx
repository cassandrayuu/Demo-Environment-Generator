import { Link } from 'react-router-dom';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Background gradient orbs for visual depth */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      {/* Main content - centered vertically */}
      <div className="flex-1 flex items-center justify-center py-16 px-8">
        <div className="max-w-5xl mx-auto w-full relative">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-3xl font-semibold text-gray-100 mb-3">Productboard Demo Tools</h1>
            <p className="text-base text-gray-400 max-w-lg mx-auto">Prepare demos faster with AI-powered content generation</p>
          </div>

          {/* Equal Grid - items-stretch for equal heights */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-stretch">
          {/* Spark Context */}
          <Link
            to="/spark-context"
            className="group relative bg-gray-900/60 backdrop-blur-sm rounded-xl p-6 transition-all duration-200 hover:bg-gray-900/80 hover:shadow-xl hover:shadow-purple-500/5 hover:-translate-y-1 border border-gray-800/60 flex flex-col"
          >
            {/* Header */}
            <div className="mb-5">
              <h2 className="text-base font-semibold text-gray-100 mb-1.5">Spark Context Generator</h2>
              <p className="text-sm text-gray-500 leading-relaxed">Generate custom context documents to feed into Spark</p>
            </div>

            {/* Visual Preview - Spark UI Mockup */}
            <div className="relative rounded-lg overflow-hidden mb-5 bg-gray-800/40 border border-gray-700/50 flex-1">
              {/* Spark Header */}
              <div className="bg-gradient-to-b from-purple-500/10 to-transparent px-4 py-6 text-center">
                <div className="w-10 h-10 mx-auto mb-3">
                  <svg viewBox="0 0 24 24" fill="none" className="w-full h-full">
                    <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" fill="url(#spark-gradient)" />
                    <defs>
                      <linearGradient id="spark-gradient" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                        <stop stopColor="#818cf8" />
                        <stop offset="1" stopColor="#c084fc" />
                      </linearGradient>
                    </defs>
                  </svg>
                </div>
                <p className="text-xs text-gray-500">What will we <span className="text-purple-400 font-medium">Spark</span> today?</p>
              </div>

              {/* Document output preview */}
              <div className="px-4 pb-4">
                <div className="grid grid-cols-2 gap-2">
                  {['Company Overview', 'Competitive Analysis', 'Key Stakeholders', 'Sales Angles'].map((doc, i) => (
                    <div key={i} className="flex items-center gap-2 px-2.5 py-2 rounded-md bg-gray-800/60">
                      <div className="w-4 h-4 rounded bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                        <svg className="w-2.5 h-2.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <span className="text-[10px] text-gray-400 truncate">{doc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Meta + Open indicator */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>~10 min · 12 docs</span>
              <span className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400">Open &rarr;</span>
            </div>

            {/* Microcopy */}
            <p className="text-xs text-gray-500 mt-3">Generates documents in Google Drive. Import via Drive integration to recreate your Spark context.</p>
          </Link>

          {/* Customer Feedback Notes */}
          <Link
            to="/insights"
            className="group relative bg-gray-900/60 backdrop-blur-sm rounded-xl p-6 transition-all duration-200 hover:bg-gray-900/80 hover:shadow-xl hover:shadow-blue-500/5 hover:-translate-y-1 border border-gray-800/60 flex flex-col"
          >
            {/* Header */}
            <div className="mb-5">
              <h2 className="text-base font-semibold text-gray-100 mb-1.5">Customer Feedback Notes</h2>
              <p className="text-sm text-gray-500 leading-relaxed">Add realistic insights to your Productboard space</p>
            </div>

            {/* Visual Preview - PB Notes UI */}
            <div className="relative rounded-lg overflow-hidden mb-5 bg-gray-800/40 border border-gray-700/50 flex-1">
              {/* Header bar */}
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-700/50">
                <span className="text-xs text-gray-500">All notes</span>
                <span className="text-xs text-blue-400 font-medium">47 notes</span>
              </div>

              {/* Notes list */}
              <div className="p-3 space-y-2">
                {[
                  { company: 'Starbucks', color: 'bg-green-600', text: "We've been impressed with the workflow..." },
                  { company: 'GoPro', color: 'bg-gray-600', text: 'Video compression quality is hurting...' },
                  { company: 'Airbnb', color: 'bg-rose-500', text: 'Location tagging has become unreliable...' },
                ].map((note, i) => (
                  <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-md bg-gray-800/60 border-l-2 border-purple-500/50">
                    <div className={`w-6 h-6 rounded ${note.color} flex items-center justify-center flex-shrink-0`}>
                      <span className="text-[10px] font-bold text-white">{note.company[0]}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-[11px] font-medium text-gray-300">{note.company}</span>
                      <p className="text-[10px] text-gray-500 truncate mt-0.5">{note.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Meta + Open indicator */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>~2-3 min · 5-50 notes</span>
              <span className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400">Open &rarr;</span>
            </div>

            {/* Microcopy */}
            <p className="text-xs text-gray-500 mt-3">Creates new feedback notes in your space, tagged to the selected company.</p>
          </Link>

          {/* Full Space Customization */}
          <Link
            to="/demo-generator"
            className="group relative bg-gray-900/60 backdrop-blur-sm rounded-xl p-6 transition-all duration-200 hover:bg-gray-900/80 hover:shadow-xl hover:shadow-teal-500/5 hover:-translate-y-1 border border-gray-800/60 flex flex-col"
          >
            {/* Header */}
            <div className="mb-5">
              <h2 className="text-base font-semibold text-gray-100 mb-1.5">Full Space Customization</h2>
              <p className="text-sm text-gray-500 leading-relaxed">Tailor your workspace with a renamed product/strategic hierarchy and realistic insights</p>
            </div>

            {/* Visual Preview - PB Hierarchy */}
            <div className="relative rounded-lg overflow-hidden mb-5 bg-gray-800/40 border border-gray-700/50 flex-1">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-700/50">
                <span className="text-xs text-gray-500">Product hierarchy</span>
                <span className="text-xs text-gray-600">Owner</span>
              </div>

              {/* Tree */}
              <div className="p-3">
                {/* Product */}
                <div className="flex items-center gap-2 px-2 py-1.5 rounded">
                  <svg className="w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                  <div className="w-5 h-5 rounded bg-purple-500/30 grid grid-cols-2 gap-0.5 p-0.5">
                    <div className="bg-purple-400 rounded-sm" />
                    <div className="bg-purple-400 rounded-sm" />
                    <div className="bg-purple-400 rounded-sm" />
                    <div className="bg-purple-400 rounded-sm" />
                  </div>
                  <span className="text-[11px] text-gray-300 font-medium">Core Engine</span>
                  <div className="ml-auto w-6 h-6 rounded-full bg-gradient-to-br from-amber-400 to-orange-500" />
                </div>

                {/* Components */}
                <div className="ml-7 border-l border-gray-700/50 pl-3 space-y-1 mt-1">
                  {[
                    { name: 'Real-time Sync', color: 'bg-purple-400' },
                    { name: 'Custom Reports', color: 'bg-teal-400' },
                    { name: 'User Management', color: 'bg-blue-400' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-2 px-2 py-1 rounded">
                      <div className={`w-2.5 h-2.5 rounded-sm ${item.color}`} />
                      <span className="text-[10px] text-gray-500">{item.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Meta + Open indicator */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>~2-3 min · Full space</span>
              <span className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400">Open &rarr;</span>
            </div>

            {/* Microcopy */}
            <p className="text-xs text-gray-500 mt-3">Renames your existing hierarchy and creates new feedback notes.</p>
          </Link>
        </div>
      </div>
    </div>

    {/* Footer - anchors the page */}
    <footer className="py-6 text-center text-xs text-gray-600">
      <p>Productboard GTM Tools</p>
    </footer>
  </div>
  );
}
