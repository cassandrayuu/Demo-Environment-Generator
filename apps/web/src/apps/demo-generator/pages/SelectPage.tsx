import { useState } from 'react';
import type { ProductInfo } from '../../../types';

interface SelectPageProps {
  company: string;
  products: ProductInfo[];
  selectedProductIds: string[];
  loading: boolean;
  error: string | null;
  analyzeWarnings: string[];
  onToggleProduct: (productId: string) => void;
  onBack: () => void;
  onGenerate: () => void;
}

/**
 * Generate example rename patterns based on company name.
 * These are representative examples, not the actual AI-generated names.
 */
function generatePreviewExamples(company: string, selectedProducts: ProductInfo[]) {
  // Example product name patterns
  const productPatterns = [
    `${company} Platform`,
    `${company} Mobile`,
    `${company} Analytics`,
    `${company} Enterprise`,
  ];

  // Example component patterns
  const componentPatterns = [
    ['Core Engine', 'Analytics Dashboard', 'Integration Hub'],
    ['Mobile Core', 'User Experience', 'Data Sync'],
    ['Admin Console', 'Reporting Module', 'API Gateway'],
  ];

  // Example feature patterns
  const featurePatterns = [
    'Real-time Data Processing',
    'Custom Report Builder',
    'Role-based Access Control',
    'Push Notifications',
    'Workflow Automation',
    'API Integration',
  ];

  // Map selected products to example outputs
  const productExamples = selectedProducts.map((product, idx) => ({
    currentName: product.name,
    newName: productPatterns[idx % productPatterns.length],
    componentCount: product.componentCount,
    featureCount: product.featureCount,
    exampleComponents: componentPatterns[idx % componentPatterns.length].slice(
      0,
      Math.min(3, product.componentCount)
    ),
    exampleFeatures: featurePatterns.slice(0, Math.min(3, product.featureCount)),
  }));

  // Strategy examples
  const objectiveExamples = [
    `Increase ${company} customer acquisition`,
    `Improve ${company} user retention`,
    `Accelerate ${company} product innovation`,
  ];

  // Insight themes
  const insightThemes = [
    'User onboarding experience',
    'Feature adoption challenges',
    'Integration requirements',
    'Performance expectations',
  ];

  return {
    products: productExamples,
    objectives: objectiveExamples,
    insightThemes,
  };
}

export function SelectPage({
  company,
  products,
  selectedProductIds,
  loading,
  error,
  analyzeWarnings,
  onToggleProduct,
  onBack,
  onGenerate,
}: SelectPageProps) {
  const [showPreview, setShowPreview] = useState(false);

  const eligibleProducts = products.filter((p) => p.eligible !== false);
  const selectedProducts = products.filter((p) => selectedProductIds.includes(p.id));

  // Can proceed with 1 or 2 products selected
  const canProceed = selectedProductIds.length >= 1 && selectedProductIds.length <= 2;

  // Check if any selected product is ineligible
  const hasIneligibleSelection = selectedProducts.some((p) => p.eligible === false);

  // Generate preview examples when products are selected
  const previewExamples = selectedProducts.length > 0
    ? generatePreviewExamples(company, selectedProducts)
    : null;

  // Collect warnings for the preview
  const previewWarnings: string[] = [];
  selectedProducts.forEach((product) => {
    if (product.componentCount < 3) {
      previewWarnings.push(
        `"${product.name}" has ${product.componentCount} component${product.componentCount === 1 ? '' : 's'}, so only ${product.componentCount} will be renamed.`
      );
    }
    if (product.featureCount === 0) {
      previewWarnings.push(
        `"${product.name}" has no features, so feature renaming will be skipped.`
      );
    }
  });

  return (
    <div className="space-y-4">
      <button
        className="text-gray-400 hover:text-primary-400 text-sm flex items-center gap-1"
        onClick={onBack}
        disabled={loading}
      >
        ← Back to setup
      </button>

      <div className="card">
        <div className="bg-gray-700/50 rounded-lg p-3 mb-4">
          <div className="text-sm text-gray-300">
            Below are existing products found in your space. Choose which products to rename for <strong className="text-primary-300">{company}</strong>.
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {products.length} products found • Select 1-2
          </div>
        </div>

        {analyzeWarnings.length > 0 && (
          <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
            {analyzeWarnings.map((warning, i) => (
              <div key={i} className="text-sm text-yellow-400">
                {warning}
              </div>
            ))}
          </div>
        )}

        <div className="space-y-3">
          {products.map((product) => {
            const isSelected = selectedProductIds.includes(product.id);
            const isEligible = product.eligible !== false;
            const isDisabled = !isEligible || (!isSelected && selectedProductIds.length >= 2);

            return (
              <button
                key={product.id}
                className={`w-full flex items-center gap-3 p-4 rounded-lg border transition-colors text-left ${
                  isSelected
                    ? 'border-primary-500 bg-primary-500/10'
                    : !isEligible
                    ? 'border-red-800/50 bg-red-900/10 opacity-60 cursor-not-allowed'
                    : isDisabled
                    ? 'border-gray-700 bg-gray-700/20 opacity-50 cursor-not-allowed'
                    : 'border-gray-700 bg-gray-700/30 hover:border-gray-600'
                }`}
                onClick={() => !isDisabled && onToggleProduct(product.id)}
                disabled={loading || isDisabled}
              >
                <div
                  className={`w-5 h-5 rounded flex-shrink-0 border-2 flex items-center justify-center ${
                    isSelected
                      ? 'bg-primary-500 border-primary-500'
                      : 'border-gray-600'
                  }`}
                >
                  {isSelected && <span className="text-white text-xs">✓</span>}
                </div>

                <div className="flex-1">
                  <div className="font-medium">{product.name}</div>
                  <div className="text-sm text-gray-400">
                    {product.componentCount} components •{' '}
                    {product.featureCount} features
                  </div>
                </div>

                {isEligible ? (
                  <span className="text-xs px-2 py-1 bg-green-600/20 text-green-400 rounded">
                    Eligible
                  </span>
                ) : (
                  <span className="text-xs px-2 py-1 bg-red-600/20 text-red-400 rounded">
                    {product.ineligibleReason || 'Not eligible'}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {eligibleProducts.length === 0 && (
          <div className="mt-4 p-4 bg-red-900/20 border border-red-700 rounded-lg text-red-400 text-center">
            No eligible products found. All products need at least 1 component.
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {hasIneligibleSelection && (
          <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
            Cannot proceed: selected product has no components.
          </div>
        )}

        {/* Preview accordion (collapsed by default) */}
        <div className="mt-4 border border-gray-700 rounded-lg overflow-hidden">
          <button
            className="w-full flex items-center justify-between p-3 bg-gray-700/30 hover:bg-gray-700/50 transition-colors text-left"
            onClick={() => setShowPreview(!showPreview)}
          >
            <span className="text-sm text-gray-300">
              Preview changes
            </span>
            <span className="text-gray-400 text-sm">
              {showPreview ? '▼' : '▶'}
            </span>
          </button>

          {showPreview && (
            <div className="p-4 bg-gray-800/50 text-sm space-y-5">
              {selectedProductIds.length === 0 ? (
                <p className="text-gray-400">Select products to see what will be renamed.</p>
              ) : previewExamples ? (
                <>
                  {/* Product Hierarchy Preview - Only show first product */}
                  {previewExamples.products.length > 0 && (
                    <div>
                      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
                        Product Hierarchy
                      </h4>
                      <div className="border-l-2 border-primary-600/50 pl-3">
                        <div className="text-gray-400 text-xs mb-1">
                          {previewExamples.products[0].currentName}
                        </div>
                        <div className="text-gray-200 font-medium flex items-center gap-2">
                          <span className="text-primary-400">→</span>
                          {previewExamples.products[0].newName}
                        </div>

                        {previewExamples.products[0].exampleComponents.length > 0 && (
                          <div className="mt-2 ml-3 space-y-1">
                            <div className="text-xs text-gray-500 mb-1">
                              Example component renames:
                            </div>
                            {previewExamples.products[0].exampleComponents.map((comp, cIdx) => (
                              <div key={cIdx} className="text-xs text-gray-400">
                                • Component {cIdx + 1} → <span className="text-gray-300">{comp}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {previewExamples.products[0].exampleFeatures.length > 0 && (
                          <div className="mt-2 ml-3 space-y-1">
                            <div className="text-xs text-gray-500 mb-1">
                              Example feature renames:
                            </div>
                            {previewExamples.products[0].exampleFeatures.slice(0, 3).map((feat, fIdx) => (
                              <div key={fIdx} className="text-xs text-gray-400">
                                • Feature {fIdx + 1} → <span className="text-gray-300">{feat}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      {selectedProducts.length > 1 && (
                        <div className="text-xs text-gray-500 mt-2">
                          + {selectedProducts.length - 1} more product{selectedProducts.length > 2 ? 's' : ''} will also be renamed
                        </div>
                      )}
                    </div>
                  )}

                  {/* Strategy Hierarchy Preview */}
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
                      Strategy Hierarchy
                    </h4>
                    <div className="text-xs text-gray-500 mb-2">
                      Objectives that will be created:
                    </div>
                    <div className="space-y-1">
                      {previewExamples.objectives.map((obj, idx) => (
                        <div key={idx} className="text-gray-300 text-sm">
                          • {obj}
                        </div>
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 mt-2">
                      + 6 initiatives and key results
                    </div>
                  </div>

                  {/* Insights Preview */}
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
                      Insights
                    </h4>
                    <div className="text-xs text-gray-500 mb-2">
                      5 customer notes will be created around:
                    </div>
                    <div className="space-y-1">
                      {previewExamples.insightThemes.map((theme, idx) => (
                        <div key={idx} className="text-gray-300 text-sm">
                          • {theme}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Warnings */}
                  {previewWarnings.length > 0 && (
                    <div className="p-3 bg-yellow-900/20 border border-yellow-700/30 rounded-lg">
                      <div className="text-xs font-medium text-yellow-400 mb-2">
                        Notes
                      </div>
                      {previewWarnings.map((warning, idx) => (
                        <div key={idx} className="text-xs text-yellow-300/80">
                          • {warning}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="text-xs text-gray-500 italic pt-2 border-t border-gray-700">
                    Actual names will be generated based on {company}'s industry and context.
                  </div>
                </>
              ) : null}
            </div>
          )}
        </div>

        <button
          className="btn btn-primary w-full mt-5"
          onClick={onGenerate}
          disabled={!canProceed || hasIneligibleSelection || loading}
        >
          {loading
            ? 'Starting...'
            : canProceed
            ? `Rename ${selectedProductIds.length} product${selectedProductIds.length > 1 ? 's' : ''} for ${company}`
            : `Select at least 1 product to rename`}
        </button>
      </div>
    </div>
  );
}
