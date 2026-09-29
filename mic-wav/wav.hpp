#pragma once

#include <cstdint>
#include <fstream>
#include <string>
#include <utility>
#include <vector>

#pragma pack(push, 1)
typedef struct WAV_HEADER
{
    char riff[4];
    std::uint32_t chunkSize;
    char wave[4];
    char fmt[4];
    std::uint32_t subchunk1Size;
    std::uint16_t audioFormat;
    std::uint16_t numChannels;
    std::uint32_t sampleRate;
    std::uint32_t byteRate;
    std::uint16_t blockAlign;
    std::uint16_t bitsPerSample;
    char data[4];
    std::uint32_t subchunk2Size;
} wav_hdr;
#pragma pack(pop)

static_assert(sizeof(wav_hdr) == 44, "Unexpected WAV header size");

struct WavFormat
{
    std::uint16_t audioFormat{1};
    std::uint16_t bitsPerSample{16};
    std::uint16_t bytesPerSample{2};
};

// Writes raw samples and WAV metadata to a wave file.
class WaveFile
{
public:
    WaveFile();
    WaveFile(std::string filePath, std::uint32_t sampleRate, std::uint16_t channels);
    ~WaveFile();

    // Disable copy operations
    WaveFile(const WaveFile&) = delete;
    WaveFile& operator=(const WaveFile&) = delete;

    // Enable move operations
    WaveFile(WaveFile&& other) noexcept;
    WaveFile& operator=(WaveFile&& other) noexcept;

    // Setters / Configuration
    void setFilePath(std::string filePath);
    void setSampleRate(std::uint32_t sampleRate);
    void setChannels(std::uint16_t channels);

    // Getters
    const std::string& getFilePath() const noexcept;
    std::uint32_t getSampleRate() const noexcept;
    std::uint16_t getChannels() const noexcept;

    // Write all samples and the WAV header to disk at once.
    bool write(const std::vector<std::uint8_t>& samples, WavFormat format) const;
    bool write(const std::uint8_t* data, std::size_t dataSize, WavFormat format) const;

    // Streaming API
    bool open(const std::string& filePath, std::uint32_t sampleRate, std::uint16_t channels, WavFormat format);
    bool writeChunk(const std::uint8_t* data, std::size_t size);
    bool writeChunk(const std::vector<std::uint8_t>& samples);
    void close();
    bool isOpen() const noexcept;

private:
    std::string filePath_;
    std::uint32_t sampleRate_{0};
    std::uint16_t channels_{0};

    // Streaming state
    mutable std::ofstream stream_;
    WavFormat streamingFormat_{};
    std::uint32_t bytesWritten_{0};
};
