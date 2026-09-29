#pragma once

#include "miniaudio.h"
#include "wav.hpp"

#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

struct AudioDeviceInfo
{
    std::string name;
    ma_device_id id;
    bool isDefault{false};
};

// RAII wrapper for miniaudio capture device.
class AudioDevice
{
public:
    AudioDevice();
    explicit AudioDevice(
        ma_uint32 sampleRate, // 0 = Auto-detect device native rate
        ma_uint16 channels = 0, // 0 = Auto-detect device native channels
        ma_format format = ma_format_unknown // ma_format_unknown (0) = Auto-detect device native format
    );
    ~AudioDevice();

    // Disable copy operations (hardware resource wrapper)
    AudioDevice(const AudioDevice&) = delete;
    AudioDevice& operator=(const AudioDevice&) = delete;

    // Disable move operations (callback holds raw 'this' pointer)
    AudioDevice(AudioDevice&&) = delete;
    AudioDevice& operator=(AudioDevice&&) = delete;

    // Device enumeration
    static std::vector<AudioDeviceInfo> getAvailableDevices();

    // Initialization and lifecycle
    // Pass sampleRate = 0, channels = 0, format = ma_format_unknown for automatic hardware format detection.
    bool init(
        ma_uint32 sampleRate = 0,
        ma_uint16 channels = 0,
        ma_format format = ma_format_unknown,
        const ma_device_id* pDeviceID = nullptr
    );

    bool start();
    bool stop();
    void uninit();

    // Status queries
    bool isInitialized() const noexcept;
    bool isStarted() const noexcept;

    // Buffer management
    const std::vector<std::uint8_t>& getBuffer() const noexcept;
    std::vector<std::uint8_t> copyBuffer() const;
    void clearBuffer();
    std::size_t getFrameCount() const;

    // Configuration queries (returns ACTUAL negotiated hardware values)
    ma_format getFormat() const noexcept;
    ma_uint32 getSampleRate() const noexcept;
    ma_uint16 getChannels() const noexcept;
    bool getWavFormat(WavFormat& wavFormat) const;

    // Save audio buffer to WAV file using negotiated format metadata
    bool saveWav(const std::string& filePath) const;

private:
    static void dataCallback(
        ma_device* pDevice,
        void* pOutput,
        const void* pInput,
        ma_uint32 frameCount);

    ma_device device_{};
    ma_device_config config_{};
    bool isInitialized_{false};
    bool isStarted_{false};
    std::vector<std::uint8_t> buffer_;
    mutable std::mutex bufferMutex_;
};

// Helper function for translating ma_format to WavFormat
bool getWavFormat(ma_format format, WavFormat& wavFormat);
