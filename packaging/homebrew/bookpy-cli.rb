class BookpyCli < Formula
  include Language::Python::Virtualenv

  desc "Discover and download legally available books from the terminal"
  homepage "https://github.com/your-org/bookpy-cli"
  url "https://files.pythonhosted.org/packages/bookpy-cli-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA256"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "bookpy-cli", shell_output("#{bin}/bookpy-cli --help")
  end
end
