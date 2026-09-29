#define MINIAUDIO_IMPLEMENTATION
#include "audio_device.hpp"
#include <iostream>

bool getWavFormat(ma_format format, WavFormat& wavFormat)
{
    const ma_uint32 bytesPerSample = ma_get_bytes_per_sample(format);
    if (bytesPerSample == 0) {
        return false;
    }

    wavFormat = {
        static_cast<std::uint16_t>(format == ma_format_f32 ? 3 : 1),
        static_cast<std::uint16_t>(bytesPerSample * 8),
        static_cast<std::uint16_t>(bytesPerSample)
    };
    return true;
}

AudioDevice::AudioDevice() = default;

AudioDevice::AudioDevice(ma_uint32 sampleRate, ma_uint16 channels, ma_format format)
{
    init(sampleRate, channels, format);
}

AudioDevice::~AudioDevice()
{
    uninit();
}

std::vector<AudioDeviceInfo> AudioDevice::getAvailableDevices()
{
    std::vector<AudioDeviceInfo> devices;
    ma_context context;
    if (ma_context_init(nullptr, 0, nullptr, &context) != MA_SUCCESS) {
        return devices;
    }

    ma_device_info* pCaptureDeviceInfos = nullptr;
    ma_uint32 captureDeviceCount = 0;
    if (ma_context_get_devices(&context, nullptr, nullptr, &pCaptureDeviceInfos, &captureDeviceCount) == MA_SUCCESS) {
        devices.reserve(captureDeviceCount);
        for (ma_uint32 i = 0; i < captureDeviceCount; ++i) {
            devices.push_back({
                pCaptureDeviceInfos[i].name,
                pCaptureDeviceInfos[i].id,
                pCaptureDeviceInfos[i].isDefault != 0
            });
        }
    }

    ma_context_uninit(&context);
    return devices;
}

bool AudioDevice::init(ma_uint32 sampleRate, ma_uint16 channels, ma_format format, const ma_device_id* pDeviceID)
{
    if (isInitialized_) {
        uninit();
    }

    config_ = ma_device_config_init(ma_device_type_capture);
    config_.capture.pDeviceID = const_cast<ma_device_id*>(pDeviceID);
    config_.capture.format   = format;
    config_.capture.channels = channels;
    config_.sampleRate       = sampleRate;
    config_.dataCallback     = AudioDevice::dataCallback;
    config_.pUserData        = this;

    if (ma_device_init(nullptr, &config_, &device_) != MA_SUCCESS) {
        isInitialized_ = false;
        return false;
    }

    isInitialized_ = true;
    return true;
}

bool AudioDevice::start()
{
    if (!isInitialized_) {
        return false;
    }
    if (isStarted_) {
        return true;
    }
    if (ma_device_start(&device_) != MA_SUCCESS) {
        return false;
    }
    isStarted_ = true;
    return true;
}

bool AudioDevice::stop()
{
    if (!isStarted_) {
        return true;
    }
    if (ma_device_stop(&device_) != MA_SUCCESS) {
        return false;
    }
    isStarted_ = false;
    return true;
}

void AudioDevice::uninit()
{
    if (isStarted_) {
        ma_device_stop(&device_);
        isStarted_ = false;
    }
    if (isInitialized_) {
        ma_device_uninit(&device_);
        isInitialized_ = false;
    }
}

bool AudioDevice::isInitialized() const noexcept
{
    return isInitialized_;
}

bool AudioDevice::isStarted() const noexcept
{
    return isStarted_;
}

const std::vector<std::uint8_t>& AudioDevice::getBuffer() const noexcept
{
    return buffer_;
}

std::vector<std::uint8_t> AudioDevice::copyBuffer() const
{
    std::lock_guard<std::mutex> lock(bufferMutex_);
    return buffer_;
}

void AudioDevice::clearBuffer()
{
    std::lock_guard<std::mutex> lock(bufferMutex_);
    buffer_.clear();
}

std::size_t AudioDevice::getFrameCount() const
{
    if (!isInitialized_) return 0;

    const ma_uint32 bytesPerFrame = ma_get_bytes_per_frame(
        device_.capture.format,
        device_.capture.channels);
    if (bytesPerFrame == 0) return 0;

    std::lock_guard<std::mutex> lock(bufferMutex_);
    return buffer_.size() / bytesPerFrame;
}

ma_format AudioDevice::getFormat() const noexcept
{
    return isInitialized_ ? device_.capture.format : ma_format_unknown;
}

ma_uint32 AudioDevice::getSampleRate() const noexcept
{
    return isInitialized_ ? device_.sampleRate : 0;
}

ma_uint16 AudioDevice::getChannels() const noexcept
{
    return isInitialized_ ? static_cast<ma_uint16>(device_.capture.channels) : 0;
}

bool AudioDevice::getWavFormat(WavFormat& wavFormat) const
{
    return ::getWavFormat(getFormat(), wavFormat);
}

bool AudioDevice::saveWav(const std::string& filePath) const
{
    WavFormat wavFormat{};
    if (!getWavFormat(wavFormat)) {
        return false;
    }

    std::vector<std::uint8_t> samplesCopy = copyBuffer();
    WaveFile waveFile(filePath, getSampleRate(), getChannels());
    return waveFile.write(samplesCopy, wavFormat);
}

void AudioDevice::dataCallback(
    ma_device* pDevice,
    void* pOutput,
    const void* pInput,
    ma_uint32 frameCount)
{
    (void)pOutput;
    if (!pDevice || !pInput || frameCount == 0) {
        return;
    }

    auto* self = static_cast<AudioDevice*>(pDevice->pUserData);
    if (!self) {
        return;
    }

    const ma_uint32 bytesPerFrame = ma_get_bytes_per_frame(
        pDevice->capture.format,
        pDevice->capture.channels);
    const ma_uint32 byteCount = frameCount * bytesPerFrame;
    const auto* samples = static_cast<const std::uint8_t*>(pInput);

    std::lock_guard<std::mutex> lock(self->bufferMutex_);
    self->buffer_.insert(
        self->buffer_.end(),
        samples,
        samples + byteCount
    );
}

#ifndef AUDIO_DEVICE_NO_MAIN
int main()
{
    // List available microphones
    auto devices = AudioDevice::getAvailableDevices();
    std::cout << "Available Capture Devices:\n";
    for (size_t i = 0; i < devices.size(); ++i) {
        std::cout << "  [" << i << "] " << devices[i].name
                  << (devices[i].isDefault ? " (Default)" : "") << "\n";
    }

    AudioDevice audioDevice;
    // Passing 0, 0, ma_format_unknown auto-detects native microphone parameters
    if (!audioDevice.init(0, 0, ma_format_unknown)) {
        std::cerr << "No usable capture device" << std::endl;
        return 1;
    }

    std::cout << "\nAuto-configured Audio Capture Device:\n";
    std::cout << "  Sample Rate: " << audioDevice.getSampleRate() << " Hz\n";
    std::cout << "  Channels:    " << audioDevice.getChannels() << "\n";
    std::cout << "  Format ID:   " << audioDevice.getFormat() << "\n";

    if (!audioDevice.start()) {
        std::cerr << "Failed to start capture device" << std::endl;
        return 1;
    }

    std::cout << "\nRecording... Press Enter to stop.\n";
    getchar();

    audioDevice.stop();

    std::cout << audioDevice.getFrameCount() << " frames captured." << std::endl;

    if (!audioDevice.saveWav("input.wav")) {
        std::cerr << "Unable to write input.wav." << std::endl;
        return 1;
    }

    std::cout << "Saved recording to input.wav!\n";
    return 0;
}
#endif