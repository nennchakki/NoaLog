# NoaLog End User License Agreement

Last updated: 2026-03-28

## 1. Introduction

NoaLog is a desktop application that uses OCR (Optical Character Recognition) to capture and log text displayed in visual novel games. It automatically captures in-game text as it appears on screen, allowing you to review, search, and manage your reading logs after gameplay.

This End User License Agreement ("EULA") sets forth the terms and conditions for using NoaLog. By downloading, installing, or using the Software, you agree to be bound by the terms of this EULA.

## 2. Definitions

"Software" refers to NoaLog and all associated source code, documentation, and binary distributions (including .exe files).

## 3. Grant of Rights

You are permitted to:

- View and read the source code for personal reference
- Download and use the Software for personal, non-commercial purposes
- Run the compiled binary (.exe) or source code for personal use

## 4. Restrictions

You may NOT, without prior written permission from the copyright holder:

- Modify, alter, adapt, or create derivative works based on the Software
- Distribute, redistribute, sublicense, sell, or otherwise transfer the Software or any copies thereof, in source or binary form
- Use the Software for commercial purposes
- Remove or alter any copyright notices or this license

## 5. Binary Distribution

Official binary distributions (.exe and other compiled formats) are provided solely by the copyright holder. Unauthorized compilation and distribution of binaries is prohibited.

## 6. Anonymous Data Submission

NoaLog includes an optional anonymous data submission feature designed to improve OCR accuracy. Please note the following:

- This feature is **OFF by default**. It only activates when you explicitly enable it in the settings
- When this feature is OFF, the Software operates **entirely locally** with no internet communication whatsoever
- The only data sent is the **difference between pre-correction and post-correction OCR text**
- Screenshots, personally identifiable information, and IP addresses are **never collected or transmitted**
- Collected data is used **solely for improving the OCR dictionary** and is never shared with third parties

## 7. Pro Version Ollama Communication

The Qwen3-VL OCR feature in the Pro version communicates exclusively with the Ollama process running on your local machine.

- Communication is limited to `localhost` (`127.0.0.1`) only
- No communication with external servers is performed
- All OCR processing is completed entirely on your PC

## 8. Privacy Policy

NoaLog respects your privacy.

- **When anonymous submission is OFF**: The Software operates entirely locally. No network communication occurs
- NoaLog contains **no analytics, advertising, or tracking** mechanisms of any kind
- There is **no automatic update checking** functionality
- Update checking is done manually by the user through the GitHub releases page

## 9. User Guidelines

- If your game text logs contain personal information (such as names or addresses), please edit or remove such content before enabling anonymous data submission
- Please comply with each game's terms of use and guidelines when using text recorded by NoaLog. NoaLog is a text logging tool only; the user is responsible for how recorded text is used

## 10. Disclaimer

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, PUNITIVE, OR CONSEQUENTIAL DAMAGES ARISING FROM THE USE OF OR INABILITY TO USE THE SOFTWARE.

## 11. Termination

This license is automatically terminated if you violate any of the restrictions set forth above. Upon termination, you must destroy all copies of the Software in your possession.

## 12. Third-Party Licenses

NoaLog uses the following open-source software:

| Software | License | Notes |
|---|---|---|
| manga-ocr | Apache License 2.0 | |
| Ollama | MIT License | Pro version only |
| Qwen3-VL | Apache License 2.0 | Pro version only |
| Avalonia UI | MIT License | |
| Microsoft.ML.OnnxRuntime | MIT License | |
| FuzzySharp | MIT License | |
| SixLabors.ImageSharp | Apache License 2.0 | |

For the full text of each license, please refer to the respective official repositories.

## 13. Contact

Copyright holder: nennchakki

For questions regarding this license or permission requests, please contact the copyright holder.
