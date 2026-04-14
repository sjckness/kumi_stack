#ifndef MY_GZ_GUI_PLUGIN__MYGUIPLUGIN_HH_
#define MY_GZ_GUI_PLUGIN__MYGUIPLUGIN_HH_

#include <memory>

#include <QStringList>

#include <gz/gui/Plugin.hh>

namespace my_gz_gui_plugin
{

class MyGuiPlugin : public gz::gui::Plugin
{
  Q_OBJECT

  Q_PROPERTY(QString pluginTitle READ PluginTitle CONSTANT)
  Q_PROPERTY(QStringList modelList READ ModelList NOTIFY modelListChanged)
  Q_PROPERTY(QStringList robotList READ RobotList NOTIFY robotListChanged)
  Q_PROPERTY(QStringList spawnableList READ SpawnableList NOTIFY spawnableListChanged)
  Q_PROPERTY(QStringList gaitList READ GaitList CONSTANT)
  Q_PROPERTY(QString cameraImageSource READ CameraImageSource NOTIFY cameraImageSourceChanged)

public:
  MyGuiPlugin();
  ~MyGuiPlugin() override;

  void LoadConfig(const tinyxml2::XMLElement *_pluginElem) override;

  QString PluginTitle() const;
  QStringList ModelList() const;
  QStringList RobotList() const;
  QStringList SpawnableList() const;
  QStringList GaitList() const;
  QString CameraImageSource() const;

signals:
  void modelListChanged();
  void robotListChanged();
  void spawnableListChanged();
  void cameraImageSourceChanged();

public slots:
  void OnSetPose(const QString &modelName,
                 double x, double y, double z, double yaw);

  void OnSpawnModel(const QString &modelUri,
                    const QString &modelName,
                    double x, double y, double z,
                    double roll, double pitch, double yaw);

  void OnRemoveModel(const QString &modelName);

  void OnSetGravity(double gz);

  void RefreshModelList();
  void OnSelectRobot(const QString &robotName);

  void OnSetEmergency(const QString &robotName, bool active);
  void OnSetWalkEnabled(const QString &robotName, bool enabled);
  void OnSetGait(const QString &robotName, const QString &gaitName);

private:
  struct Impl;
  std::unique_ptr<Impl> impl;
};

}  // namespace my_gz_gui_plugin

#endif  // MY_GZ_GUI_PLUGIN__MYGUIPLUGIN_HH_
