#include "wav.hpp"

WaveFile::WaveFile() = default;

WaveFile::WaveFile(std::string filePath, std::uint32_t sampleRate, std::uint16_t channels)
    : filePath_(std::move(filePath)), sampleRate_(sampleRate), channels_(channels)
{
}

WaveFile::~WaveFile()
{
    close();
}

WaveFile::WaveFile(WaveFile&& other) noexcept
    : filePath_(std::move(other.filePath_)),
      sampleRate_(other.sampleRate_),
      channels_(other.channels_),
      stream_(std::move(other.stream_)),
      streamingFormat_(other.streamingFormat_),
      bytesWritten_(other.bytesWritten_)
{
    other.sampleRate_ = 0;
    other.channels_ = 0;
    other.bytesWritten_ = 0;
}

WaveFile& WaveFile::operator=(WaveFile&& other) noexcept
{
    if (this != &other)
    {
        close();
        filePath_ = std::move(other.filePath_);
        sampleRate_ = other.sampleRate_;
        channels_ = other.channels_;
        stream_ = std::move(other.stream_);
        streamingFormat_ = other.streamingFormat_;
        bytesWritten_ = other.bytesWritten_;

        other.sampleRate_ = 0;
        other.channels_ = 0;
        other.bytesWritten_ = 0;
    }
    return *this;
}

void WaveFile::setFilePath(std::string filePath)
{
    filePath_ = std::move(filePath);
}

void WaveFile::setSampleRate(std::uint32_t sampleRate)
{
    sampleRate_ = sampleRate;
}

void WaveFile::setChannels(std::uint16_t channels)
{
    channels_ = channels;
}

const std::string& WaveFile::getFilePath() const noexcept
{
    return filePath_;
}

std::uint32_t WaveFile::getSampleRate() const noexcept
{
    return sampleRate_;
}

std::uint16_t WaveFile::getChannels() const noexcept
{
    return channels_;
}

bool WaveFile::write(const std::vector<std::uint8_t>& samples, WavFormat format) const
{
    return write(samples.data(), samples.size(), format);
}

bool WaveFile::write(const std::uint8_t* data, std::size_t dataSize, WavFormat format) const
{
    if (filePath_.empty() || channels_ == 0 || sampleRate_ == 0) {
        return false;
    }

    if (format.bitsPerSample == 0 || format.bytesPerSample == 0) {
        return false;
    }

    const std::uint64_t dataSize64 = dataSize;
    const std::uint64_t riffSize = 36 + dataSize64;
    if (dataSize64 > 0xFFFFFFFFULL || riffSize > 0xFFFFFFFFULL) {
        return false;
    }

    std::ofstream output(filePath_, std::ios::binary);
    if (!output) {
        return false;
    }

    wav_hdr header{
        {'R', 'I', 'F', 'F'},
        static_cast<std::uint32_t>(riffSize),
        {'W', 'A', 'V', 'E'},
        {'f', 'm', 't', ' '},
        16,
        format.audioFormat,
        channels_,
        sampleRate_,
        sampleRate_ * channels_ * format.bytesPerSample,
        static_cast<std::uint16_t>(channels_ * format.bytesPerSample),
        format.bitsPerSample,
        {'d', 'a', 't', 'a'},
        static_cast<std::uint32_t>(dataSize64)
    };

    output.write(reinterpret_cast<const char*>(&header), sizeof(header));
    if (data && dataSize > 0) {
        output.write(reinterpret_cast<const char*>(data), static_cast<std::streamsize>(dataSize));
    }

    return output.good();
}

bool WaveFile::open(const std::string& filePath, std::uint32_t sampleRate, std::uint16_t channels, WavFormat format)
{
    close();

    if (filePath.empty() || sampleRate == 0 || channels == 0) {
        return false;
    }
    if (format.bitsPerSample == 0 || format.bytesPerSample == 0) {
        return false;
    }

    stream_.open(filePath, std::ios::binary);
    if (!stream_) {
        return false;
    }

    filePath_ = filePath;
    sampleRate_ = sampleRate;
    channels_ = channels;
    streamingFormat_ = format;
    bytesWritten_ = 0;

    // Write placeholder header (44 bytes)
    wav_hdr header{};
    stream_.write(reinterpret_cast<const char*>(&header), sizeof(header));
    return stream_.good();
}

bool WaveFile::writeChunk(const std::uint8_t* data, std::size_t size)
{
    if (!stream_.is_open() || !data || size == 0) {
        return false;
    }

    if (static_cast<std::uint64_t>(bytesWritten_) + size > 0xFFFFFFFFULL) {
        return false;
    }

    stream_.write(reinterpret_cast<const char*>(data), static_cast<std::streamsize>(size));
    if (stream_.good()) {
        bytesWritten_ += static_cast<std::uint32_t>(size);
        return true;
    }
    return false;
}

bool WaveFile::writeChunk(const std::vector<std::uint8_t>& samples)
{
    return writeChunk(samples.data(), samples.size());
}

void WaveFile::close()
{
    if (stream_.is_open()) {
        if (bytesWritten_ > 0 || stream_.tellp() > 0) {
            stream_.seekp(0, std::ios::beg);
            const std::uint32_t riffSize = 36 + bytesWritten_;
            wav_hdr header{
                {'R', 'I', 'F', 'F'},
                riffSize,
                {'W', 'A', 'V', 'E'},
                {'f', 'm', 't', ' '},
                16,
                streamingFormat_.audioFormat,
                channels_,
                sampleRate_,
                sampleRate_ * channels_ * streamingFormat_.bytesPerSample,
                static_cast<std::uint16_t>(channels_ * streamingFormat_.bytesPerSample),
                streamingFormat_.bitsPerSample,
                {'d', 'a', 't', 'a'},
                bytesWritten_
            };
            stream_.write(reinterpret_cast<const char*>(&header), sizeof(header));
        }
        stream_.close();
    }
    bytesWritten_ = 0;
}

bool WaveFile::isOpen() const noexcept
{
    return stream_.is_open();
}
