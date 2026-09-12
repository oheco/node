#ifndef SRC_NODE_OHOS_COMPAT_H_
#define SRC_NODE_OHOS_COMPAT_H_

#include <string_view>
#include <vector>

#if defined(__OHOS__) && defined(_LIBCPP_VERSION) && _LIBCPP_VERSION < 16000
#define NODE_OHOS_LEGACY_LIBCXX 1

namespace node {
// libc++ 15 has ranges algorithms, but lacks split_view and elements_view.
// Match views::split for a single delimiter, including trailing empty fields
// and the empty input producing no fields. The views borrow the input string.
inline std::vector<std::string_view> OhosSplitStringView(std::string_view input,
                                                      char delimiter) {
  std::vector<std::string_view> result;
  if (input.empty()) return result;
  size_t start = 0;
  for (;;) {
    size_t end = input.find(delimiter, start);
    result.emplace_back(input.substr(
        start, end == std::string_view::npos ? end : end - start));
    if (end == std::string_view::npos) break;
    start = end + 1;
  }
  return result;
}
}  // namespace node
#else
#define NODE_OHOS_LEGACY_LIBCXX 0
#endif

#endif  // SRC_NODE_OHOS_COMPAT_H_
