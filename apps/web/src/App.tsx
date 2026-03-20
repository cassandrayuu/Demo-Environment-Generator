import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { DemoGeneratorApp } from './apps/demo-generator/DemoGeneratorApp';
import { InsightsApp } from './apps/insights/InsightsApp';
import { SparkContextApp } from './apps/spark-context/SparkContextApp';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/demo-generator/*" element={<DemoGeneratorApp />} />
        <Route path="/insights/*" element={<InsightsApp />} />
        <Route path="/spark-context/*" element={<SparkContextApp />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
