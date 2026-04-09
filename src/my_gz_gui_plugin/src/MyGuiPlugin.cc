#include "my_gz_gui_plugin/MyGuiPlugin.hh"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <filesystem>
#include <map>
#include <set>
#include <string>
#include <vector>

#include <QBuffer>
#include <QImage>
#include <QMetaObject>
#include <QStringList>
#include <QProcess>

#include <ament_index_cpp/get_package_share_directory.hpp>
#include <gz/gui/Application.hh>
#include <gz/gui/MainWindow.hh>
#include <gz/math/Quaternion.hh>
#include <gz/msgs/boolean.pb.h>
#include <gz/msgs/empty.pb.h>
#include <gz/msgs/entity.pb.h>
#include <gz/msgs/entity_factory.pb.h>
#include <gz/msgs/image.pb.h>
#include <gz/msgs/physics.pb.h>
#include <gz/msgs/pose.pb.h>
#include <gz/msgs/scene.pb.h>
#include <gz/msgs/stringmsg.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/transport/Node.hh>

namespace my_gz_gui_plugin
{

struct MyGuiPlugin::Impl
{
  gz::transport::Node node;

  std::string topicSpawn{"/world/default/create"};
  std::string topicRemove{"/world/default/remove"};
  std::string topicSetPose{"/world/default/set_pose"};
  std::string topicPhysics{"/world/default/set_physics"};
  std::string topicSceneInfo;  // derived from spawn topic if not set

  std::string topicEmergency{"/kumi_behavior/emergency"};
  std::string topicWalkEnabled{"/kumi_seq_traj_controller/enabled"};
  std::string topicGait{"/kumi_seq_traj_controller/gait"};

  std::map<std::string, gz::transport::Node::Publisher> emergencyPubs;
  std::map<std::string, gz::transport::Node::Publisher> walkEnabledPubs;
  std::map<std::string, gz::transport::Node::Publisher> gaitPubs;

  QStringList modelList;
  QStringList robotList;
  QStringList spawnableList;
  QStringList gaitList{"walk", "frontflip", "backwalk", "backflip", "accovacciato"};
  std::set<std::string> knownRobotNames{"bruno"};
  QString cameraImageSource;
  std::string currentCameraTopic;
  std::set<std::string> cameraSubscriptions;
};

namespace
{

std::vector<std::filesystem::path> ResourceRoots()
{
  std::vector<std::filesystem::path> roots;
  std::set<std::string> seen;

  const std::array<const char *, 2> envVars{
    "GZ_SIM_RESOURCE_PATH",
    "IGN_GAZEBO_RESOURCE_PATH",
  };

  for (const auto *envVar : envVars)
  {
    const char *value = std::getenv(envVar);
    if (!value)
      continue;

    std::string allPaths(value);
    std::size_t start = 0;
    while (start <= allPaths.size())
    {
      auto end = allPaths.find(':', start);
      auto token = allPaths.substr(start, end - start);
      if (!token.empty() && seen.insert(token).second)
        roots.emplace_back(token);

      if (end == std::string::npos)
        break;
      start = end + 1;
    }
  }

  return roots;
}

QStringList DiscoverSpawnables()
{
  std::set<std::string> resources;
  resources.insert("kumi");

  for (const auto &root : ResourceRoots())
  {
    if (!std::filesystem::exists(root) || !std::filesystem::is_directory(root))
      continue;

    for (const auto &entry : std::filesystem::directory_iterator(root))
    {
      if (!entry.is_directory())
        continue;

      const auto configPath = entry.path() / "model.config";
      const auto sdfPath = entry.path() / "model.sdf";
      if (!std::filesystem::exists(configPath) && !std::filesystem::exists(sdfPath))
        continue;

      resources.insert("model://" + entry.path().filename().string());
    }
  }

  QStringList list;
  for (const auto &resource : resources)
    list.append(QString::fromStdString(resource));

  return list;
}

QString DefaultNameFromUri(const QString &_uri)
{
  const auto trimmed = _uri.trimmed();
  if (trimmed.isEmpty())
    return {};

  auto normalized = trimmed;
  if (normalized.endsWith('/'))
    normalized.chop(1);

  const auto lastSlash = normalized.lastIndexOf('/');
  const auto lastColon = normalized.lastIndexOf(':');
  const auto splitIndex = std::max(lastSlash, lastColon);
  auto baseName = splitIndex >= 0 ? normalized.mid(splitIndex + 1) : normalized;
  baseName.replace('-', '_');
  return baseName;
}

std::string TopicForRobot(const QString &_robotName, const std::string &_suffix)
{
  const auto trimmed = _robotName.trimmed().toStdString();
  if (trimmed.empty())
    return {};

  return "/" + trimmed + "/" + _suffix;
}

QString CameraTopicForRobot(const QString &_robotName)
{
  const auto trimmed = _robotName.trimmed();
  if (trimmed.isEmpty())
    return {};

  return "/" + trimmed + "/front_camera/image";
}

QString ImageToDataUrl(const gz::msgs::Image &_msg)
{
  QImage image;

  switch (_msg.pixel_format_type())
  {
    case gz::msgs::RGB_INT8:
      image = QImage(
        reinterpret_cast<const uchar *>(_msg.data().data()),
        static_cast<int>(_msg.width()),
        static_cast<int>(_msg.height()),
        static_cast<int>(_msg.step()),
        QImage::Format_RGB888).copy();
      break;
    case gz::msgs::BGR_INT8:
      image = QImage(
        reinterpret_cast<const uchar *>(_msg.data().data()),
        static_cast<int>(_msg.width()),
        static_cast<int>(_msg.height()),
        static_cast<int>(_msg.step()),
        QImage::Format_BGR888).copy();
      break;
    case gz::msgs::RGBA_INT8:
      image = QImage(
        reinterpret_cast<const uchar *>(_msg.data().data()),
        static_cast<int>(_msg.width()),
        static_cast<int>(_msg.height()),
        static_cast<int>(_msg.step()),
        QImage::Format_RGBA8888).copy();
      break;
    default:
      return {};
  }

  if (image.isNull())
    return {};

  QByteArray bytes;
  QBuffer buffer(&bytes);
  buffer.open(QIODevice::WriteOnly);
  image.save(&buffer, "PNG");
  return "data:image/png;base64," + bytes.toBase64();
}

bool PublishRosStringTopic(const QString &_topic, const QString &_value)
{
  if (_topic.trimmed().isEmpty())
    return false;

  QProcess process;
  process.start(
    "ros2",
    QStringList{
      "topic",
      "pub",
      "--once",
      _topic,
      "std_msgs/msg/String",
      QString("{data: \"%1\"}").arg(_value),
    });

  if (!process.waitForStarted(1000) || !process.waitForFinished(10000) ||
      process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0)
  {
    qWarning() << "ros2 string topic pub failed on" << _topic
               << process.readAllStandardError();
    return false;
  }

  return true;
}

}  // namespace

MyGuiPlugin::MyGuiPlugin()
  : impl(std::make_unique<Impl>())
{
}

MyGuiPlugin::~MyGuiPlugin() = default;

void MyGuiPlugin::LoadConfig(const tinyxml2::XMLElement *_pluginElem)
{
  if (this->title.empty())
    this->title = "Control pannel";

  if (!_pluginElem)
  {
    return;
  }

  auto elem = _pluginElem->FirstChildElement("topic_spawn");
  if (elem && elem->GetText())
    this->impl->topicSpawn = elem->GetText();

  elem = _pluginElem->FirstChildElement("topic_remove");
  if (elem && elem->GetText())
    this->impl->topicRemove = elem->GetText();

  elem = _pluginElem->FirstChildElement("topic_set_pose");
  if (elem && elem->GetText())
    this->impl->topicSetPose = elem->GetText();

  elem = _pluginElem->FirstChildElement("topic_physics");
  if (elem && elem->GetText())
    this->impl->topicPhysics = elem->GetText();

  elem = _pluginElem->FirstChildElement("topic_scene_info");
  if (elem && elem->GetText())
    this->impl->topicSceneInfo = elem->GetText();

  elem = _pluginElem->FirstChildElement("topic_emergency");
  if (elem && elem->GetText())
    this->impl->topicEmergency = elem->GetText();

  elem = _pluginElem->FirstChildElement("topic_walk_enabled");
  if (elem && elem->GetText())
    this->impl->topicWalkEnabled = elem->GetText();

  elem = _pluginElem->FirstChildElement("topic_gait");
  if (elem && elem->GetText())
    this->impl->topicGait = elem->GetText();

  elem = _pluginElem->FirstChildElement("title");
  if (elem && elem->GetText())
    this->title = elem->GetText();

  // Parse gait list from XML if provided
  elem = _pluginElem->FirstChildElement("gaits");
  if (elem && elem->GetText())
  {
    QString gaitsStr = QString::fromUtf8(elem->GetText());
    this->impl->gaitList = gaitsStr.split(",", Qt::SkipEmptyParts);
    for (auto &g : this->impl->gaitList)
      g = g.trimmed();
  }

  // Derive scene_info topic from spawn topic if not explicitly set
  // e.g. "/world/my_empty/create" -> "/world/my_empty/scene/info"
  if (this->impl->topicSceneInfo.empty())
  {
    auto &spawn = this->impl->topicSpawn;
    auto pos = spawn.rfind('/');
    if (pos != std::string::npos)
      this->impl->topicSceneInfo = spawn.substr(0, pos) + "/scene/info";
    else
      this->impl->topicSceneInfo = "/world/default/scene/info";
  }

}

QString MyGuiPlugin::PluginTitle() const
{
  return QString::fromStdString(this->title);
}

QStringList MyGuiPlugin::ModelList() const
{
  return this->impl->modelList;
}

QStringList MyGuiPlugin::RobotList() const
{
  return this->impl->robotList;
}

QStringList MyGuiPlugin::SpawnableList() const
{
  return this->impl->spawnableList;
}

QStringList MyGuiPlugin::GaitList() const
{
  return this->impl->gaitList;
}

QString MyGuiPlugin::CameraImageSource() const
{
  return this->impl->cameraImageSource;
}

void MyGuiPlugin::RefreshModelList()
{
  const auto newSpawnableList = DiscoverSpawnables();
  if (newSpawnableList != this->impl->spawnableList)
  {
    this->impl->spawnableList = newSpawnableList;
    emit spawnableListChanged();
  }

  gz::msgs::Empty req;
  gz::msgs::Scene rep;
  bool result{false};

  if (!this->impl->node.Request(
        this->impl->topicSceneInfo, req, 2000u, rep, result) || !result)
  {
    qWarning() << "Scene info service call failed on topic:"
               << QString::fromStdString(this->impl->topicSceneInfo);
    return;
  }

  QStringList newList;
  QStringList newRobotList;
  for (int i = 0; i < rep.model_size(); ++i)
  {
    const auto modelName = QString::fromStdString(rep.model(i).name());
    newList.append(modelName);

    if (this->impl->knownRobotNames.count(rep.model(i).name()) > 0 &&
        !newRobotList.contains(modelName))
      newRobotList.append(modelName);
  }

  if (newList != this->impl->modelList)
  {
    this->impl->modelList = newList;
    emit modelListChanged();
  }

  if (newRobotList != this->impl->robotList)
  {
    this->impl->robotList = newRobotList;
    emit robotListChanged();
  }
}

void MyGuiPlugin::OnSelectRobot(const QString &robotName)
{
  const auto cameraTopic = CameraTopicForRobot(robotName);
  this->impl->currentCameraTopic = cameraTopic.toStdString();

  if (cameraTopic.isEmpty())
  {
    if (!this->impl->cameraImageSource.isEmpty())
    {
      this->impl->cameraImageSource.clear();
      emit cameraImageSourceChanged();
    }
    return;
  }

  const auto topicKey = cameraTopic.toStdString();
  if (this->impl->cameraSubscriptions.insert(topicKey).second)
  {
    std::function<void(const gz::msgs::Image &)> callback =
      [this, topicKey](const gz::msgs::Image &_msg)
      {
        if (this->impl->currentCameraTopic != topicKey)
          return;

        const auto imageUrl = ImageToDataUrl(_msg);
        if (imageUrl.isEmpty())
          return;

        QMetaObject::invokeMethod(
          this,
          [this, imageUrl]()
          {
            if (this->impl->cameraImageSource == imageUrl)
              return;

            this->impl->cameraImageSource = imageUrl;
            emit cameraImageSourceChanged();
          },
          Qt::QueuedConnection);
      };

    this->impl->node.Subscribe<gz::msgs::Image>(topicKey, callback);
  }
}

void MyGuiPlugin::OnSetEmergency(const QString &robotName, bool active)
{
  const auto topic = TopicForRobot(robotName, "kumi_behavior/emergency");
  if (topic.empty())
    return;

  auto &pub = this->impl->emergencyPubs[topic];
  if (!pub)
    pub = this->impl->node.Advertise<gz::msgs::Boolean>(topic);

  gz::msgs::Boolean msg;
  msg.set_data(active);
  pub.Publish(msg);
}

void MyGuiPlugin::OnSetWalkEnabled(const QString &robotName, bool enabled)
{
  const auto topic = TopicForRobot(robotName, "kumi_seq_traj_controller/enabled");
  if (topic.empty())
    return;

  auto &pub = this->impl->walkEnabledPubs[topic];
  if (!pub)
    pub = this->impl->node.Advertise<gz::msgs::Boolean>(topic);

  gz::msgs::Boolean msg;
  msg.set_data(enabled);
  pub.Publish(msg);
}

void MyGuiPlugin::OnSetGait(const QString &robotName, const QString &gaitName)
{
  const auto topic = TopicForRobot(robotName, "kumi_seq_traj_controller/gait");
  if (topic.empty())
    return;

  auto &pub = this->impl->gaitPubs[topic];
  if (!pub)
    pub = this->impl->node.Advertise<gz::msgs::StringMsg>(topic);

  gz::msgs::StringMsg msg;
  msg.set_data(gaitName.toStdString());
  pub.Publish(msg);
}

void MyGuiPlugin::OnSetPose(const QString &modelName,
                            double x, double y, double z, double yaw)
{
  gz::msgs::Pose req;
  req.set_name(modelName.toStdString());
  req.mutable_position()->set_x(x);
  req.mutable_position()->set_y(y);
  req.mutable_position()->set_z(z);

  auto q = gz::math::Quaterniond(0, 0, yaw);
  req.mutable_orientation()->set_x(q.X());
  req.mutable_orientation()->set_y(q.Y());
  req.mutable_orientation()->set_z(q.Z());
  req.mutable_orientation()->set_w(q.W());

  gz::msgs::Boolean rep;
  bool result{false};
  if (!this->impl->node.Request(
        this->impl->topicSetPose, req, 2000u, rep, result) || !result)
  {
    qWarning() << "SetPose service call failed for model:" << modelName;
  }
}

void MyGuiPlugin::OnSpawnModel(const QString &modelUri,
                               const QString &modelName,
                               double x, double y, double z,
                               double roll, double pitch, double yaw)
{
  const auto trimmedUri = modelUri.trimmed();
  if (trimmedUri.isEmpty())
  {
    qWarning() << "Spawn skipped because no model URI was selected";
    return;
  }

  auto resolvedName = modelName.trimmed();
  if (resolvedName.isEmpty())
    resolvedName = DefaultNameFromUri(trimmedUri);

  if (resolvedName.isEmpty())
  {
    qWarning() << "Spawn skipped because model name is empty";
    return;
  }

  if (this->impl->modelList.contains(resolvedName))
  {
    qWarning() << "Spawn skipped because model name already exists:" << resolvedName;
    return;
  }

  if (trimmedUri == "kumi")
  {
    QString descriptionShare;
    QString controlShare;
    try
    {
      descriptionShare = QString::fromStdString(
        ament_index_cpp::get_package_share_directory("kumi_description"));
      controlShare = QString::fromStdString(
        ament_index_cpp::get_package_share_directory("kumi_control"));
    }
    catch (const std::exception &e)
    {
      qWarning() << "Unable to resolve package share directories for kumi spawn:"
                 << e.what();
      return;
    }

    QProcess process;
    process.start(
      "xacro",
      QStringList{
        descriptionShare + "/urdf/kumi.xacro",
        "use_sim:=true",
        "enable_sensors:=true",
        "robot_name:=" + resolvedName,
        "ros_namespace:=" + resolvedName,
        "pkg_share:=" + descriptionShare,
        "control_config:=" + controlShare + "/config/trajectory_control_config.yaml",
      });

    if (!process.waitForStarted(1000) || !process.waitForFinished(10000) ||
        process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0)
    {
      qWarning() << "xacro processing failed for kumi:"
                 << process.readAllStandardError();
      return;
    }

    const auto sdfString = process.readAllStandardOutput();
    if (sdfString.trimmed().isEmpty())
    {
      qWarning() << "xacro returned empty robot description for:" << resolvedName;
      return;
    }

    gz::msgs::EntityFactory req;
    req.set_sdf(sdfString.toStdString());
    req.set_name(resolvedName.toStdString());
    req.mutable_pose()->mutable_position()->set_x(x);
    req.mutable_pose()->mutable_position()->set_y(y);
    req.mutable_pose()->mutable_position()->set_z(z);
    auto q = gz::math::Quaterniond(roll, pitch, yaw);
    req.mutable_pose()->mutable_orientation()->set_x(q.X());
    req.mutable_pose()->mutable_orientation()->set_y(q.Y());
    req.mutable_pose()->mutable_orientation()->set_z(q.Z());
    req.mutable_pose()->mutable_orientation()->set_w(q.W());

    gz::msgs::Boolean rep;
    bool result{false};
    if (!this->impl->node.Request(
          this->impl->topicSpawn, req, 5000u, rep, result) || !result)
    {
      qWarning() << "Spawn service call failed for kumi:" << resolvedName;
      return;
    }

    PublishRosStringTopic("/kumi_sim/register_robot", resolvedName);
    this->impl->knownRobotNames.insert(resolvedName.toStdString());
    this->RefreshModelList();
    return;
  }

  gz::msgs::EntityFactory req;
  req.set_sdf_filename(trimmedUri.toStdString());
  req.set_name(resolvedName.toStdString());
  req.mutable_pose()->mutable_position()->set_x(x);
  req.mutable_pose()->mutable_position()->set_y(y);
  req.mutable_pose()->mutable_position()->set_z(z);
  auto q = gz::math::Quaterniond(roll, pitch, yaw);
  req.mutable_pose()->mutable_orientation()->set_x(q.X());
  req.mutable_pose()->mutable_orientation()->set_y(q.Y());
  req.mutable_pose()->mutable_orientation()->set_z(q.Z());
  req.mutable_pose()->mutable_orientation()->set_w(q.W());

  gz::msgs::Boolean rep;
  bool result{false};
  if (!this->impl->node.Request(
        this->impl->topicSpawn, req, 2000u, rep, result) || !result)
  {
    qWarning() << "Spawn service call failed for model:" << resolvedName;
    return;
  }

  this->RefreshModelList();
}

void MyGuiPlugin::OnRemoveModel(const QString &modelName)
{
  const auto trimmedName = modelName.trimmed();
  if (trimmedName.isEmpty())
  {
    qWarning() << "Remove skipped because no entity was selected";
    return;
  }

  gz::msgs::Entity req;
  req.set_name(trimmedName.toStdString());
  req.set_type(gz::msgs::Entity::MODEL);

  gz::msgs::Boolean rep;
  bool result{false};
  if (!this->impl->node.Request(
        this->impl->topicRemove, req, 2000u, rep, result) || !result)
  {
    qWarning() << "Remove service call failed for model:" << trimmedName;
    return;
  }

  PublishRosStringTopic("/kumi_sim/unregister_robot", trimmedName);
  this->impl->knownRobotNames.erase(trimmedName.toStdString());
  this->RefreshModelList();
}

void MyGuiPlugin::OnSetGravity(double gz)
{
  gz::msgs::Physics req;
  req.mutable_gravity()->set_z(gz);

  gz::msgs::Boolean rep;
  bool result{false};
  if (!this->impl->node.Request(
        this->impl->topicPhysics, req, 2000u, rep, result) || !result)
  {
    qWarning() << "SetGravity service call failed";
  }
}

}  // namespace my_gz_gui_plugin

GZ_ADD_PLUGIN(
  my_gz_gui_plugin::MyGuiPlugin,
  gz::gui::Plugin
)
