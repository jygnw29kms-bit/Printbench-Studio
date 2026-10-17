#include "PrintbenchUpdateService.hpp"

#include "GeneratedConfig.hpp"
#include "../Utils/Http.hpp"

#include <algorithm>
#include <array>
#include <boost/algorithm/string.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <sstream>
#include <tuple>

namespace Slic3r::GUI {
namespace {

constexpr const char* kReleaseApi = "https://api.github.com/repos/jygnw29kms-bit/Printbench-Studio/releases?per_page=20";
constexpr const char* kTagPrefix = "printbench-v";

std::array<int, 3> parse_version(std::string version)
{
    if (boost::algorithm::starts_with(version, kTagPrefix))
        version.erase(0, std::char_traits<char>::length(kTagPrefix));

    std::array<int, 3> out {0, 0, 0};
    std::stringstream ss(version);
    std::string part;
    for (size_t i = 0; i < out.size() && std::getline(ss, part, '.'); ++i) {
        try { out[i] = std::stoi(part); }
        catch (...) { return {0, 0, 0}; }
    }
    return out;
}

bool newer_than_current(const std::string& candidate)
{
    return parse_version(candidate) > parse_version(PRINTBENCH_VERSION);
}

} // namespace

const char* PrintbenchUpdateService::current_version()
{
    return PRINTBENCH_VERSION;
}

const char* PrintbenchUpdateService::release_api_url()
{
    return kReleaseApi;
}

void PrintbenchUpdateService::check(bool stable_only, Result result)
{
    auto http = Http::get(kReleaseApi);
    http.header("accept", "application/vnd.github+json")
        .header("x-github-api-version", "2022-11-28")
        .timeout_connect(5)
        .timeout_max(10)
        .on_error([result](std::string, std::string error, unsigned status) {
            result(std::nullopt, status == 0 ? error : "HTTP " + std::to_string(status));
        })
        .on_complete([stable_only, result](std::string body, unsigned status) {
            if (status != 200) {
                result(std::nullopt, "HTTP " + std::to_string(status));
                return;
            }

            try {
                boost::property_tree::ptree root;
                std::stringstream json(body);
                boost::property_tree::read_json(json, root);

                std::optional<PrintbenchUpdateInfo> best;
                for (const auto& entry : root) {
                    const auto& node = entry.second;
                    const std::string tag = node.get<std::string>("tag_name", "");
                    if (!boost::algorithm::starts_with(tag, kTagPrefix))
                        continue;

                    const bool prerelease = node.get<bool>("prerelease", false);
                    const bool draft = node.get<bool>("draft", false);
                    if (draft || (stable_only && prerelease) || !newer_than_current(tag))
                        continue;

                    PrintbenchUpdateInfo candidate;
                    candidate.version = tag.substr(std::char_traits<char>::length(kTagPrefix));
                    candidate.release_url = node.get<std::string>("html_url", "");
                    candidate.notes = node.get<std::string>("body", "");
                    candidate.prerelease = prerelease;

                    if (!best || parse_version(kTagPrefix + candidate.version) > parse_version(kTagPrefix + best->version))
                        best = std::move(candidate);
                }
                result(best, {});
            } catch (const std::exception& e) {
                result(std::nullopt, e.what());
            }
        });
    http.perform();
}

} // namespace Slic3r::GUI
