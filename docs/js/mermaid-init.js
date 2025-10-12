document.addEventListener('DOMContentLoaded', function () {
  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: true,
      securityLevel: 'loose' // pozwala na <br/> w etykietach węzłów itp.
    });
  }
});
