import './globals.css';

export const metadata = {
  title: 'DeCad — Circuit Workbench',
  description: 'AI-assisted schematic capture & circuit workbench with native KiCad validation and Specctra DSN routing.',
  authors: [{ name: 'Raghav Krishna', url: 'https://github.com/JRK14' }],
  creator: 'Raghav Krishna (JRK)',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
