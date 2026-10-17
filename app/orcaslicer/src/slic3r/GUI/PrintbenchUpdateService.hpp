#pragma once

#include <functional>
#include <optional>
#include <string>

namespace Slic3r::GUI {

struct PrintbenchUpdateInfo
{
    std::string version;
    std::string release_url;
    std::string notes;
    bool prerelease { false };
};

class PrintbenchUpdateService
{
public:
    using Result = std::function<void(std::optional<PrintbenchUpdateInfo>, std::string)>;

    static void check(bool stable_only, Result result);
    static const char* current_version();
    static const char* release_api_url();
};

} // namespace Slic3r::GUI
